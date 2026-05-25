FROM python:3.11-slim
WORKDIR /app
COPY . /app/
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
