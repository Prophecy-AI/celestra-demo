FROM mlebench-env

# Build args from mle-bench
ARG SUBMISSION_DIR
ENV SUBMISSION_DIR=${SUBMISSION_DIR}
ARG LOGS_DIR
ENV LOGS_DIR=${LOGS_DIR}
ARG CODE_DIR
ENV CODE_DIR=${CODE_DIR}
ARG AGENT_DIR
ENV AGENT_DIR=${AGENT_DIR}

# Create required directories
RUN mkdir -p ${LOGS_DIR} ${CODE_DIR} ${AGENT_DIR}

ARG CONDA_ENV_NAME=agent

# Copy requirements first (for Docker layer caching)
COPY requirements.txt ${AGENT_DIR}/requirements.txt

# Install agent dependencies
RUN conda run -n ${CONDA_ENV_NAME} pip install -r ${AGENT_DIR}/requirements.txt && \
    conda clean -afy

# Pre-install common ML packages to save time during competition
RUN conda run -n ${CONDA_ENV_NAME} pip install \
    xgboost>=2.0.0 \
    lightgbm>=4.0.0 \
    catboost>=1.2.0 \
    scikit-learn>=1.3.0 \
    pandas>=2.0.0 \
    numpy>=1.24.0 \
    matplotlib>=3.7.0 \
    seaborn>=0.12.0 \
    scipy>=1.11.0 \
    && conda clean -afy

# Install PyTorch with CUDA support for GPU
RUN conda run -n ${CONDA_ENV_NAME} pip install \
    torch>=2.0.0 \
    torchvision>=0.15.0 \
    torchaudio>=2.0.0 \
    --index-url https://download.pytorch.org/whl/cu118 \
    && conda clean -afy

# Install TensorFlow with GPU support (optional, for flexibility)
RUN conda run -n ${CONDA_ENV_NAME} pip install \
    tensorflow>=2.13.0 \
    && conda clean -afy

# Copy all agent files
COPY . ${AGENT_DIR}

# Set working directory to CODE_DIR (agent's workspace)
WORKDIR ${CODE_DIR}
