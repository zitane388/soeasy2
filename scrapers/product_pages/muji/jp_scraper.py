# scrapers/muji/jp_scraper.py

from scrapers.base_scraper import BaseScraper

class MujiJPScraper(BaseScraper):

    SITE_KEY = "muji_jp"

    def request_main(self, url):
        """
        메인 상품 페이지 요청 (기본 상세설명 수집용)
        """
        return self._request_html(url, mode="RAW")

    def request_color_html(self, color_url, color_name=None):
        """
        MUJI는 색상별로 URL이 다르므로 URL을 그대로 요청한다.
        (주로 색상별 메인 이미지와 가격 수집용)
        """
        return self._request_html(
            color_url,
            mode="COLOR",
            color=color_name
        )

    def request_size_chart(self, url):
        """
        📐 사이즈표 전용 요청
        확장 프로그램의 HandlerMujiJP에서 'SIZE_CHART' 구분을 인식하여
        '仕様・サイズ' 탭을 클릭한 뒤의 HTML을 가져옵니다.
        """
        return self._request_html(
            url, 
            mode="SIZE_CHART"
        )