import json
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup


class SuperSportsJapanParser:
    def parse(self, scraper, original_url, first_html):
        soup = BeautifulSoup(first_html, "html.parser")
        next_data = self._extract_next_data(soup)
        product = self._extract_product_payload(next_data)

        original_name = self._pick_first_text(
            product.get("name"),
            self._extract_text_css(soup, "span.product-name"),
            self._extract_text_css(soup, "h1"),
        )
        detail_description = self._extract_detail_description(product, soup)
        size_html_raw, size_headers, size_rows = self._extract_size_chart_from_text(
            product=product,
            soup=soup,
            detail_description=detail_description,
        )
        model_number = self._extract_model_number(product, original_name, soup)
        product_brand = self._extract_product_brand(product, soup)

        colors, sizes, options = self._extract_options(product, soup)
        prices = self._extract_prices(product, colors, soup)
        images = self._extract_images(product, soup)

        return {
            "original_name": original_name,
            "model_number": model_number,
            "product_brand": product_brand,
            "price": next(iter(prices.values()), "") if prices else "",
            "prices": prices,
            "sizes": sizes,
            "images": images,
            "detail_description": detail_description,
            "colors": colors,
            "options": options,
            "size_html_raw": size_html_raw,
            "size_headers_original": size_headers,
            "size_rows_original": size_rows,
        }

    def _extract_next_data(self, soup: BeautifulSoup):
        node = soup.find("script", id="__NEXT_DATA__")
        if not node:
            return {}
        raw = node.string or node.get_text(strip=True) or ""
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def _extract_product_payload(self, next_data):
        if not isinstance(next_data, dict):
            return {}

        product = (
            next_data.get("props", {})
            .get("pageProps", {})
            .get("product", {})
        )
        if isinstance(product, dict) and product:
            return product

        found = self._find_first_dict_with_keys(next_data, ["features", "price"])
        return found if isinstance(found, dict) else {}

    def _find_first_dict_with_keys(self, value, keys):
        if isinstance(value, dict):
            if all(k in value for k in keys):
                return value
            for v in value.values():
                found = self._find_first_dict_with_keys(v, keys)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = self._find_first_dict_with_keys(item, keys)
                if found:
                    return found
        return None

    def _extract_options(self, product, soup):
        features = product.get("features", [])
        colors = []
        sizes = []

        for f in features if isinstance(features, list) else []:
            f_type = str(f.get("type", "")).lower()
            alternatives = f.get("alternatives", [])
            if not isinstance(alternatives, list):
                continue

            if "color" in f_type:
                for alt in alternatives:
                    name = self._pick_first_text(alt.get("text"), alt.get("name"))
                    code = alt.get("code")
                    if not name:
                        continue
                    colors.append(
                        {
                            "name": name,
                            "code": code,
                            "image": self._normalize_image_url(
                                alt.get("imgUrl") or alt.get("image")
                            ),
                        }
                    )
            elif "size" in f_type:
                for alt in alternatives:
                    name = self._pick_first_text(alt.get("text"), alt.get("name"))
                    code = alt.get("code")
                    status = str(alt.get("status", "")).lower()
                    stock = alt.get("stock")
                    disabled = False
                    if "out" in status or "sold" in status:
                        disabled = True
                    if isinstance(stock, int) and stock <= 0:
                        disabled = True
                    if not name:
                        continue
                    sizes.append(
                        {
                            "name": name,
                            "code": code,
                            "disabled": disabled,
                        }
                    )

        if not colors:
            color_label = self._extract_text_css(
                soup, "ul.wrap.select li.color p.label"
            )
            if color_label:
                colors.append({"name": color_label, "code": None, "image": None})

        if not sizes:
            for btn in soup.select("button.select-size"):
                name = btn.get_text(strip=True)
                if not name:
                    continue
                disabled = bool(btn.get("disabled")) or (
                    "disabled" in (btn.get("class") or [])
                )
                sizes.append({"name": name, "code": None, "disabled": disabled})

        options = []
        if colors:
            options.append(
                {
                    "group_name": "color",
                    "values": [
                        {
                            "name": c.get("name"),
                            "code": c.get("code"),
                            "image": c.get("image"),
                            "disabled": False,
                        }
                        for c in colors
                    ],
                }
            )

        if sizes:
            options.append(
                {
                    "group_name": "size",
                    "values": [
                        {
                            "name": s.get("name"),
                            "code": s.get("code"),
                            "disabled": bool(s.get("disabled", False)),
                        }
                        for s in sizes
                    ],
                }
            )

        return colors, sizes, options

    def _extract_prices(self, product, colors, soup):
        price_obj = product.get("price", {})
        num = None
        if isinstance(price_obj, dict):
            num = (
                price_obj.get("taxInclusive")
                or price_obj.get("value")
                or price_obj.get("price")
            )
        if num is None:
            text_price = self._extract_text_css(soup, "strong.sale")
            num = self._digits_only(text_price)

        if num is None:
            return {}

        price_str = self._format_jpy(num)
        if colors:
            mapped = {}
            for c in colors:
                key = c.get("code") or c.get("name")
                if key:
                    mapped[key] = price_str
            if mapped:
                return mapped
        return {"default": price_str}

    def _extract_images(self, product, soup):
        out = []
        media = product.get("media", [])
        if isinstance(media, list):
            for m in media:
                if not isinstance(m, dict):
                    continue
                url = (
                    m.get("imgUrl")
                    or m.get("imageUrl")
                    or m.get("url")
                    or m.get("src")
                )
                if url:
                    n = self._normalize_image_url(url)
                    if n:
                        out.append(n)

        if not out:
            for img in soup.select("div.thumbnails img"):
                src = img.get("src") or img.get("data-src")
                if src:
                    n = self._normalize_image_url(src)
                    if n:
                        out.append(n)

        if not out:
            # fallback: supersports product asset pattern
            for img in soup.select("img[src*='/ec/img/']"):
                src = img.get("src") or img.get("data-src")
                n = self._normalize_image_url(src)
                if n:
                    out.append(n)

        # de-dup keep order
        seen = set()
        uniq = []
        for x in out:
            if x in seen:
                continue
            seen.add(x)
            uniq.append(x)
        return uniq

    def _extract_detail_description(self, product, soup):
        description = product.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()

        spec_node = soup.select_one("#spec-content .spec")
        if spec_node:
            return spec_node.get_text(" ", strip=True)

        return ""

    def _extract_model_number(self, product, original_name, soup):
        # 0) Label-based extraction has highest priority.
        labeled = self._extract_labeled_product_fields(soup)
        for key in (
            "メーカー品番",
            "メーカー品番:",
            "메이커품번",
            "품번",
            "모델",
            "모델번호",
            "model",
            "model number",
        ):
            v = labeled.get(key)
            if v:
                m = re.search(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b", str(v).upper())
                if m:
                    return m.group(0)

        candidates = []

        # Prefer explicit model/manufacturer-part style keys first.
        preferred_keys = (
            "modelNumber",
            "modelNo",
            "model",
            "makerPartNumber",
            "manufacturerPartNumber",
            "partNumber",
            "sku",
            "productCode",
            "itemCode",
            "id",
        )
        for k in preferred_keys:
            v = product.get(k)
            if v:
                candidates.append(str(v))

        # onboarding model_area fallback
        css_candidates = [
            "div.model-number",
            "span.model-number",
            "[data-testid='model-number']",
            "div.product-number",
        ]
        for css in css_candidates:
            t = self._extract_text_css(soup, css)
            if not t:
                continue
            candidates.extend(
                re.findall(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b", str(t).upper())
            )

        text = original_name or ""
        candidates.extend(re.findall(r"\b[A-Z0-9]{2,}-[A-Z0-9]{2,}\b", text.upper()))

        return self._pick_best_model_candidate(candidates, text)

    def _extract_size_chart_from_text(self, product, soup, detail_description):
        """
        Parse SuperSports measurement text blocks such as:
        【実寸サイズ】
        ●Sサイズ詳細:【ウエスト】71cm【ヒップ】96.5cm...
        """
        candidates = []

        description = product.get("description")
        if isinstance(description, str) and description.strip():
            candidates.append(description.strip())

        if isinstance(detail_description, str) and detail_description.strip():
            candidates.append(detail_description.strip())

        spec_node = soup.select_one("#spec-content .spec")
        if spec_node:
            spec_text = spec_node.get_text("\n", strip=True)
            if spec_text:
                candidates.append(spec_text)

        parsed_headers = []
        parsed_rows = []

        for text in candidates:
            headers, rows = self._parse_measurement_rows(text)
            if headers and rows:
                parsed_headers = headers
                parsed_rows = rows
                break

        if not parsed_headers or not parsed_rows:
            return "", [], []

        html = self._build_size_table_html(parsed_headers, parsed_rows)
        return html, parsed_headers, parsed_rows

    def _parse_measurement_rows(self, text):
        if not isinstance(text, str) or not text.strip():
            return [], []

        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if "実寸サイズ" not in normalized:
            return [], []

        lines = [ln.strip() for ln in normalized.split("\n") if ln.strip()]
        row_pattern = re.compile(
            r"^[\u25cf\u2022\u30fb]?\s*([^\s:：]+?)\s*サイズ(?:詳細)?\s*[:：]\s*(.+)$"
        )
        measure_pattern = re.compile(
            r"【\s*([^】]+?)\s*】\s*([\-+]?\d+(?:\.\d+)?\s*(?:cm|mm|m|in|inch|インチ)?)"
        )

        measure_order = []
        parsed = []

        for line in lines:
            m = row_pattern.match(line)
            if not m:
                continue

            size_name = (m.group(1) or "").strip()
            tail = (m.group(2) or "").strip()
            if not size_name or not tail:
                continue

            row_map = {}
            for mm in measure_pattern.finditer(tail):
                key = (mm.group(1) or "").strip()
                value = (mm.group(2) or "").strip()
                if not key:
                    continue
                if key not in measure_order:
                    measure_order.append(key)
                row_map[key] = value

            if row_map:
                parsed.append((size_name, row_map))

        if not parsed or not measure_order:
            return [], []

        headers = ["サイズ"] + measure_order
        rows = []
        for size_name, row_map in parsed:
            row = [size_name] + [row_map.get(k, "") for k in measure_order]
            rows.append(row)

        return headers, rows

    def _build_size_table_html(self, headers, rows):
        if not headers or not rows:
            return ""

        th_html = "".join(f"<th>{h}</th>" for h in headers)
        tr_html = []
        for row in rows:
            td_html = "".join(f"<td>{cell}</td>" for cell in row)
            tr_html.append(f"<tr>{td_html}</tr>")

        return (
            "<table class='size-chart'>"
            f"<thead><tr>{th_html}</tr></thead>"
            f"<tbody>{''.join(tr_html)}</tbody>"
            "</table>"
        )

    def _extract_labeled_product_fields(self, soup):
        """
        Extract label-value pairs from product detail blocks such as:
        <p class="product-item"><span class="title">メーカー品番</span><span class="description">HM6803-109</span></p>
        """
        out = {}
        rows = soup.select("div.product-number p.product-item")
        for row in rows:
            title = row.select_one("span.title")
            desc = row.select_one("span.description")
            if not title or not desc:
                continue
            k = title.get_text(" ", strip=True)
            v = desc.get_text(" ", strip=True)
            if not k or not v:
                continue
            out[k] = v
            out[k.lower()] = v
        return out

    def _pick_best_model_candidate(self, candidates, original_name):
        if not candidates:
            return None

        name_u = (original_name or "").upper()
        seen = set()
        scored = []
        for c in candidates:
            token = str(c).strip().upper()
            if not token or token in seen:
                continue
            seen.add(token)

            score = 0
            # Strong model-shape signal.
            if re.search(r"[A-Z]", token) and re.search(r"\d", token):
                score += 3
            if "-" in token:
                score += 2
            # Product-id-like tokens such as A-10893435601 should be de-prioritized.
            if re.fullmatch(r"[A-Z]-\d{8,}", token):
                score -= 4
            # If model token appears in title, it is usually the right one.
            if token and token in name_u:
                score += 3

            scored.append((score, token))

        if not scored:
            return None

        scored.sort(key=lambda x: (x[0], len(x[1])), reverse=True)
        best = scored[0][1]
        return best if best else None

    def _extract_product_brand(self, product, soup):
        brand = product.get("brandName") or product.get("brand")
        if isinstance(brand, dict):
            parsed = self._pick_first_text(brand.get("name"), brand.get("text"))
            if parsed:
                return parsed
        if isinstance(brand, str):
            parsed = brand.strip()
            if parsed:
                return parsed

        # onboarding brand_area fallback:
        # <span class="brand-name"><a ...>NIKE</a></span>
        css_candidates = [
            "span.brand-name a",
            "span.brand-name",
            "a[href*='brand=']",
        ]
        for css in css_candidates:
            parsed = self._extract_text_css(soup, css)
            if parsed:
                return parsed

        return None

    def _extract_text_css(self, soup, css):
        node = soup.select_one(css)
        if not node:
            return ""
        return node.get_text(" ", strip=True)

    def _pick_first_text(self, *values):
        for v in values:
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    def _digits_only(self, text):
        if not text:
            return None
        digits = "".join(ch for ch in str(text) if ch.isdigit())
        return int(digits) if digits else None

    def _format_jpy(self, value):
        try:
            n = int(value)
        except Exception:
            return str(value)
        return f"JPY {n:,}"

    def _normalize_image_url(self, url):
        if not isinstance(url, str):
            return None

        s = url.strip().replace("\\/", "/")
        s = s.strip("\"' ")

        if not s:
            return None

        if s.startswith("//"):
            s = "https:" + s
        elif s.startswith("/"):
            s = urljoin("https://www.supersports.com", s)

        # trailing punctuation sometimes appears in copied/embedded strings
        while s and s[-1] in ".,;":
            s = s[:-1]

        if not (s.startswith("http://") or s.startswith("https://")):
            return None

        return s
