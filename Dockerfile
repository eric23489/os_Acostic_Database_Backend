# 使用官方的 Python 3.14 輕量版作為基底
FROM python:3.14-slim

# 設定容器內的工作目錄
WORKDIR /app

# 先複製 requirements.txt 到容器內
# 這樣做是為了利用 Docker 的快取機制，加速之後的構建
COPY requirements.txt .

# 安裝 Python 套件
# --no-cache-dir 可以減少映像檔的大小
RUN pip install --no-cache-dir -r requirements.txt

# 將當前目錄的所有程式碼複製到容器的工作目錄
COPY . .

RUN chmod +x entrypoint.sh

# 告訴容器啟動時要執行的指令
# host 0.0.0.0 代表允許外部連線，port 設定為 80
CMD ["./entrypoint.sh"]
