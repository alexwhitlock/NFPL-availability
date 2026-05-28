FROM python:3.11-slim

WORKDIR /app

# Copy proxy and data files
COPY web/nfpl_proxy.py .
COPY web/site-data.json .
COPY check_nfpl.py .

# No extra dependencies needed — only stdlib

# Listen on 0.0.0.0:5004 (not just localhost)
EXPOSE 5004

CMD ["python3", "nfpl_proxy.py"]
