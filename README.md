# 洋聲聲學資料庫與後端

## 📖 專案簡介 (Introduction)

本系統基於 Python FastAPI 與 Docker 等技術堆疊，專為處理高通量水下錄音數據設計。後端採用 PostgreSQL 結合 PostGIS 處理佈放資訊，並以 MinIO 建構可擴充的音檔儲存層。

## 核心功能 (Features)

- 待補

## 技術棧 (Tech Stack)

- **Python 3.14**
- **FastAPI** - 現代化的 Web 框架
- **Uvicorn** - ASGI 伺服器
- **Alembic** - 資料庫遷移工具
- **PostgreSQL / Postgis** - 資料庫
- **Docker & Docker Compose** - 容器化部署
- **MinIO** - 連接NAS接口

## 安裝與設定 (Installation & Setup)

### 1. 先決條件 (Prerequisites)

- Python 3.14+
- Postgis 17
- Docker 29.0.1+

### 2. 下載專案 (Clone Repository)

```bash
git clone https://github.com/OceanSound-TW/os_Acostic_Database_Backend.git
cd os_Acostic_Database_Backend
```

### 3. 建立虛擬環境 (Create Virtual Environment)

- 本機執行

    本機執行還須另外下載 [Postgis](https://postgis.net/), 建議Docker執行

```bash
# Windows
python -m venv .venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source venv/bin/activate
```

- Docker 執行可跳過

### 4. 安裝相依套件 (Install Dependencies)

```bash
pip install -r requirements.txt
```

### 5. 環境變數設定 (Environment Variables)

.env檔撰寫

``` txt
POSTGRES_USER=[DB_USERNAME]
POSTGRES_PASSWORD=[DB_PASSWORD]
POSTGRES_DB=[DB_NAME]
POSTGRES_IP_ADDRESS=[localhost]
POSTGRES_PORT=5431
POSTGRES_PORT_OUT=5431

SECRET_KEY=[SET_SECRET_KEY]

APP_PORT=80
APP_PORT_OUT=8000

MINIO_IP_ADDRESS=[MINIO_IP]
MINIO_PORT=9000
AWS_ACCESS_KEY_ID=[MINIO_USERNAME]
AWS_SECRET_ACCESS_KEY=[MINIO_PASSWORD]
MINIO_BUCKET_NAME=data

```

### 6. 如何使用 (Usage)

- 本機執行
  - 資料庫建立

    ``` bash
    alembic upgrade head # 建立與更新欄位
    ```

  - 執行

    ``` bash
    uvicorn app.main:app --host 0.0.0.0 --port 80 
    ```

- Docker執行
  - DB掛載資料夾預設為`D:/Program Files/Docker_DB_volume/os-acoustic-postgres`, 可以進入`docker-compose.yml`修改

    ```bash
    docker-compose up --build
    ```

  - 確定alembic有連接到DB

    ``` bash
    alembic current
    ```
  
  - 資料庫建立

    ``` bash
    alembic upgrade head # 建立與更新欄位
    ```

  - 執行

    ``` bash
    docker-compose up --build
    ```

### 7. 如何測試 (Testing)

### 8. 注意事項

- 資料庫遷移 (Alembic & PostGIS)

    本專案使用 PostGIS 擴充套件。為了防止 `alembic revision --autogenerate` 誤刪 PostGIS 的系統表格，我們在 `env.py` 中加入了過濾機制。

  - `env.py` 設定

    使用 include_object 函數忽略以下表格：

    ``` python
    IGNORE_TABLES = {
    'spatial_ref_sys', 'topology', 'layer', 'direction_lookup',
    'tiger', 'us_gaz', 'zip_state', 'zip_state_loc'
    }
    # PostGIS Tiger Geocoder 產生的表格通常很多，可以用前綴判斷
    IGNORE_PREFIXES = {
    'tiger_', 'addr', 'bg', 'county', 'cousub', 'edges', 'faces', 
    'featnames', 'loader_', 'pagc_', 'place', 'secondary_', 'state', 
    'street_', 'tabblock', 'tract', 'zcta5', 'zip_lookup', 'geocode_settings'
    }
    ```
  
  - `script.py.mako` 設定

    要使得`alembic`寫遷移腳本的時候加入`geoalchemy2`讓postgis可以正常使用, 在檔案中加入

    ``` python
    import geoalchemy2  
    ```
