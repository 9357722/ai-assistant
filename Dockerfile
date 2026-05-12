# 1. 基础镜像：轻量级Python 3.11
FROM python:3.11-slim

# 2. 设置工作目录
WORKDIR /app

# 3. 复制项目文件到容器里
COPY . /app/

# 4. 安装依赖
RUN pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 5. 暴露端口
EXPOSE 8000

# 6. 启动命令
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]