FROM python:3.9

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Add Jupyter configuration
RUN mkdir -p /root/.jupyter
COPY jupyter_notebook_config.py /root/.jupyter/

COPY . .

# Expose Jupyter port
EXPOSE 8888

# Update CMD to run Jupyter by default
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*