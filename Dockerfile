# Render / Railway / Fly.io 等の PaaS 向け Streamlit コンテナ。
# Streamlit Community Cloud では Dockerfile は不要（requirements.txt を自動適用）。
FROM python:3.11-slim

WORKDIR /app

# 依存を先にインストール（ビルドキャッシュを効かせる）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# FastF1 キャッシュの書き込み先（永続ボリュームをマウントする場合は上書き可）
ENV FASTF1_CACHE=/tmp/f1_cache

# PaaS は $PORT を注入する。未設定時は 8501。
ENV PORT=8501
EXPOSE 8501

# シェル形式で $PORT を展開する
CMD streamlit run streamlit_app.py --server.port=$PORT --server.address=0.0.0.0
