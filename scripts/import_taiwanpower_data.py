import os
import sys
import requests
from datetime import datetime

# 將專案根目錄加入 Python 路徑，確保可以匯入 app 模組
sys.path.append(os.getcwd())

from scripts.geo import dms_to_dd

# 設定 API URL 與 登入資訊 (請依實際環境修改)
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "aaa@example.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "aaa")


def get_token():
    """登入並取得 Access Token"""
    url = f"{API_BASE_URL}/users/login"
    try:
        # OAuth2PasswordRequestForm 格式
        response = requests.post(
            url, data={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        print(f"❌ 登入失敗: {e}")
        if response.status_code == 401:
            print(
                "   請確認 ADMIN_EMAIL 與 ADMIN_PASSWORD 是否正確，且 API 伺服器已啟動。"
            )
        sys.exit(1)


def import_data():
    print("🚀 開始匯入 TaiwanPower 2nd 資料 (透過 API)...")

    # 1. 取得 Token
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # --- 1. 建立 Project ---
        project_name = "taiwanpower2nd"

        # 取得所有專案並檢查是否存在
        resp = requests.get(f"{API_BASE_URL}/projects/", headers=headers)
        resp.raise_for_status()
        projects = resp.json()
        project = next((p for p in projects if p["name"] == project_name), None)

        if not project:
            print(f"➕ 建立專案: {project_name}")
            payload = {"name": project_name, "description": "PacificOcean"}
            resp = requests.post(
                f"{API_BASE_URL}/projects/", json=payload, headers=headers
            )
            resp.raise_for_status()
            project = resp.json()
        else:
            print(f"✅ 專案已存在: {project_name}")

        project_id = project["id"]

        # --- (前置作業) 準備 Recorder ---
        # 取得所有 Recorder
        resp = requests.get(f"{API_BASE_URL}/recorders/", headers=headers)
        resp.raise_for_status()
        recorders_data = resp.json()

        # 處理分頁 (如果有) 或直接列表
        if isinstance(recorders_data, dict) and "items" in recorders_data:
            recorders = recorders_data["items"]
        elif isinstance(recorders_data, list):
            recorders = recorders_data
        else:
            recorders = []

        recorder_map = {}
        for r in recorders:
            if "name" in r:
                recorder_map[r["name"]] = r
            elif "model" in r and "sn" in r:
                # 對應下方 rec_name = f"{item['model']}-{item['serial']}"
                recorder_map[f"{r['model']}-{r['sn']}"] = r

        # (名稱, 經度, 緯度, 水深, 布放時間, 回收時間, 儀器型號, 儀器序號, 靈敏度)
        site_data = [
            {
                "name": "TPC1",
                "lon_str": "120°20.360' E",
                "lat_str": "24°5.500' N",
                "depth_str": "14.6 m",
                "deploy_str": "2024/6/13 06:13:00",
                "return_str": "2024/6/29 07:03:00",
                "model": "ST600",
                "serial": "7505",
                "sensitivity": -174.5,
            },
            {
                "name": "TPC2",
                "lon_str": "120° 15.954'E",
                "lat_str": "24°5.951’N",
                "depth_str": "46.7 m",
                "deploy_str": "2024/6/13 06:46:00",
                "return_str": "2024/6/29 07:39:00",
                "model": "ST600",
                "serial": "8444",
                "sensitivity": -176.9,
            },
            {
                "name": "TPC3",
                "lon_str": "120°15.477' E",
                "lat_str": "24°3.341' N",
                "depth_str": "41.9 m",
                "deploy_str": "2024/6/13 08:27:00",
                "return_str": "2024/6/29 09:30:00",
                "model": "ST600",
                "serial": "7784",
                "sensitivity": -175.8,
            },
            {
                "name": "TPC4",
                "lon_str": "120°12.775' E",
                "lat_str": "24°5.856' N",
                "depth_str": "41.8 m",
                "deploy_str": "2024/6/13 07:18:00",
                "return_str": "2024/6/29 08:14:00",
                "model": "ST600",
                "serial": "7785",
                "sensitivity": -175.7,
            },
            {
                "name": "TPC5",
                "lon_str": "120°10.885' E",
                "lat_str": "24°3.696' N",
                "depth_str": "40.9 m",
                "deploy_str": "2024/6/13 07:47:00",
                "return_str": "2024/6/29 08:49:00",
                "model": "ST600",
                "serial": "7787",
                "sensitivity": -175.9,
            },
        ]

        # 取得該專案下的所有 Points (假設 API 支援 filter 或我們手動 filter)
        # 這裡簡化為取得所有 Points 後在 Python 過濾
        resp = requests.get(
            f"{API_BASE_URL}/points/?project_id={project_id}", headers=headers
        )
        resp.raise_for_status()
        all_points = resp.json()

        # --- 迴圈匯入 Point 與 Deployment ---
        for item in site_data:
            name = item["name"]
            lon = dms_to_dd(item["lon_str"])
            lat = dms_to_dd(item["lat_str"])
            depth = float(item["depth_str"].replace("m", "").strip())

            # 處理 Recorder
            rec_name = f"{item['model']}-{item['serial']}"
            if rec_name not in recorder_map:
                print(f"➕ 建立 Recorder: {rec_name}")
                recorder_payload = {
                    "name": rec_name,
                    "brand": "Ocean Instruments",
                    "model": item["model"],
                    "sn": item["serial"],
                    "sensitivity": item["sensitivity"],
                }
                resp = requests.post(
                    f"{API_BASE_URL}/recorders/",
                    json=recorder_payload,
                    headers=headers,
                )
                resp.raise_for_status()
                recorder_map[rec_name] = resp.json()

            recorder_id = recorder_map[rec_name]["id"]

            # --- 2. 建立 Point ---
            # 檢查 Point 是否存在
            point = next(
                (
                    p
                    for p in all_points
                    if p["name"] == name and p["project_id"] == project_id
                ),
                None,
            )

            point_payload = {
                "name": name,
                "project_id": project_id,
                "gps_lat_plan": lat,
                "gps_lon_plan": lon,
                "depth_plan": depth,
            }

            if not point:
                print(f"  ➕ 建立測站: {name}")
                resp = requests.post(
                    f"{API_BASE_URL}/points/", json=point_payload, headers=headers
                )
                resp.raise_for_status()
                point = resp.json()
                all_points.append(point)
            else:
                print(f"  🔄 更新測站: {name} (ID: {point['id']})")
                resp = requests.put(
                    f"{API_BASE_URL}/points/{point['id']}",
                    json=point_payload,
                    headers=headers,
                )
                resp.raise_for_status()
                point = resp.json()

            # --- 3. 建立 Deployment ---
            # 檢查是否已有 Deployment (假設 API 支援查詢，這裡先略過查詢直接嘗試建立，若重複可能會報錯或需要處理)
            # 為了簡化，我們假設如果 Point 剛建立或更新，就嘗試建立 Deployment
            # 實務上應該先 GET /deployments/?point_id=... 檢查

            # 這裡先查詢該 Point 的 Deployments
            resp = requests.get(
                f"{API_BASE_URL}/deployments/?point_id={point['id']}", headers=headers
            )
            # 若 API 不支援 query param，可能回傳所有，需自行 filter
            if resp.status_code == 200:
                deployments = resp.json()
                # 假設 deployments 列表包含該 point 的所有佈放
                # 檢查是否有 phase=1
                has_deployment = any(d.get("phase") == 1 for d in deployments)
            else:
                has_deployment = False

            deploy_dt = datetime.strptime(item["deploy_str"], "%Y/%m/%d %H:%M:%S")
            return_dt = datetime.strptime(item["return_str"], "%Y/%m/%d %H:%M:%S")

            if not has_deployment:
                deployment_payload = {
                    "point_id": point["id"],
                    "recorder_id": recorder_id,
                    "phase": 1,
                    "gps_lat_exe": lat,
                    "gps_lon_exe": lon,
                    "depth_exe": depth,
                    "deploy_time": deploy_dt.isoformat(),
                    "return_time": return_dt.isoformat(),
                    "sensitivity": item["sensitivity"],
                    "status": "finished",
                }
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/deployments/",
                        json=deployment_payload,
                        headers=headers,
                    )
                    resp.raise_for_status()
                    print(f"    -> 建立 Deployment (Phase 1)")
                except requests.exceptions.HTTPError as e:
                    print(f"    -> 建立 Deployment 失敗: {e.response.text}")
            else:
                print(f"    -> Deployment (Phase 1) 已存在，跳過")

        print("✨ 資料匯入完成！")

    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        raise


if __name__ == "__main__":
    import_data()
