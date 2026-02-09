import time
import json
import bcrypt
import pybase64
import base64
import requests
import mimetypes
import os
import uuid
from pathlib import Path

# -----------------------------------------
# 환경설정
# -----------------------------------------
CLIENT_ID = "6AAvxdsWrpeKD25X9B1tKb"
CLIENT_SECRET = "$2a$04$7Dbq61G3SPwz2CUi6gKeKO"
SELLER_ID = "ncp_1otxmo_01"

# 출고지 / 반품지 주소록 ID (당신이 제공한 값)
SHIPPING_ADDR_ID = 106712350      # 일본 출고지
RETURN_ADDR_ID = 106712349        # 국내 반품지

# -----------------------------------------
# 1) 토큰 발급
# -----------------------------------------
def get_token():
    timestamp = str(int(time.time() * 1000))
    raw = f"{CLIENT_ID}_{timestamp}".encode("utf-8")

    hashed = bcrypt.hashpw(raw, CLIENT_SECRET.encode("utf-8"))
    signature = pybase64.standard_b64encode(hashed).decode("utf-8")

    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {
        "client_id": CLIENT_ID,
        "timestamp": timestamp,
        "client_secret_sign": signature,
        "grant_type": "client_credentials",
        "type": "SELF",
        "sellerId": SELLER_ID,
    }

    resp = requests.post(url, data=data)
    print("[TOKEN]", resp.text)
    resp.raise_for_status()
    return resp.json()["access_token"]

# -----------------------------------------
# 2) 외부 이미지 다운로드 → 로컬 temp 저장
# -----------------------------------------
def download_image(url: str, save_path: str):
    print(f"[IMG] downloading: {url}")
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(r.content)
    return save_path

def upload_image_naver(token, local_path):
    url = "https://api.commerce.naver.com/external/v1/product-images/upload"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json;charset=UTF-8"
    }

    filename = os.path.basename(local_path)

    with open(local_path, "rb") as f:
        files = {
            "imageFiles": (filename, f, "image/jpeg")   # 🔥 핵심: imageFiles
        }

        resp = requests.post(url, headers=headers, files=files)

    print("[IMG UPLOAD]", resp.text)
    resp.raise_for_status()
    return resp.json()["images"][0]["url"]


# -----------------------------------------
# 4) Smartstore 구매대행 상품 등록
# -----------------------------------------
def upload_purchase_agent(token, image_url):

    url = "https://api.commerce.naver.com/external/v2/products"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "originProduct": {
            "statusType": "SALE",
            "leafCategoryId": "50000826",        # 여성의류 상의 (예시)

            "name": "구매대행 테스트 상품",
            "detailContent": "이 상품은 테스트용 구매대행 상품입니다.",

            "images": {
                "representativeImage": {
                    "url": image_url
                }
            },

            "salePrice": 10000,
            "stockQuantity": 10,

            "deliveryInfo": {
                "deliveryType": "DELIVERY",
                "deliveryAttributeType": "NORMAL",
                "deliveryCompany": "CJGLS",
                "deliveryFee": {
                    "deliveryFeeType": "FREE"
                },

                "claimDeliveryInfo": {
                    "returnDeliveryCompanyPriorityType": "PRIMARY",
                    "returnDeliveryFee": 0,
                    "exchangeDeliveryFee": 0,
                    "shippingAddressId": SHIPPING_ADDR_ID,
                    "returnAddressId": RETURN_ADDR_ID,
                    "freeReturnInsuranceYn": False
                }
            },

            "detailAttribute": {
                "minorPurchasable": False,
                
                "afterServiceInfo": {
                    "afterServiceTelephoneNumber": "02-0000-0000",
                    "afterServiceGuideContent": "테스트 AS 안내"
                },

                "originAreaInfo": {
                    "originAreaType": "INCLUDE_IN_DETAILS",
                    "content": "상세설명에 표시",
                    "originAreaCode": "03",
                    "wholeOriginAreaName": "상세설명에 표시",
                    "plural": False
                },

                "purchaseQuantityInfo": {
                    "minPurchaseQuantity": 2,
                    "maxPurchaseQuantityPerId": 10,
                    "maxPurchaseQuantityPerOrder": 10
                },

                "productInfoProvidedNotice": {
                    "productInfoProvidedNoticeType": "ETC",
                    "etc": {
                        "itemName": "의류",
                        "modelName": "테스트모델",
                        "manufacturer": "UNIQLO JAPAN",
                        "afterServiceDirector": "홍길동"
                    }
                }
                
            }

        },

        "smartstoreChannelProduct": {
            "naverShoppingRegistration": False,
            "channelProductDisplayStatusType": "SUSPENSION"
        }
    }
    # print(json.dumps(body, indent=4, ensure_ascii=False))  # 🔥 여기에 추가!
    resp = requests.post(url, headers=headers, json=body)
    print("[PRODUCT]", resp.text)
    resp.raise_for_status()
    return resp.json()

# -----------------------------------------
# 실행
# -----------------------------------------
if __name__ == "__main__":
    IMG_URL = "https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/481253/item/goods_03_481253_3x4.jpg"
    LOCAL_IMG = "temp_img.jpg"
    token = get_token()

    # 테스트용 유니클로 이미지
    test_image_url = "https://image.uniqlo.com/UQ/ST3/AsianCommon/imagesgoods/481253/item/goods_03_481253_3x4.jpg"

    # 2) 이미지 다운로드 → 로컬 저장
    download_image(IMG_URL, LOCAL_IMG)

    # 3) 로컬 파일을 네이버 API로 업로드 → CDN URL 획득
    uploaded = upload_image_naver(token, LOCAL_IMG)
    print("업로드된 네이버 이미지 URL =", uploaded)


    # 3) 상품 등록
    result = upload_purchase_agent(token, uploaded)

    print("\n=== 상품 등록 성공 ===")
    print(json.dumps(result, indent=4, ensure_ascii=False))
