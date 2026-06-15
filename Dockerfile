# base.Dockerfile
FROM python:3.12-bookworm
WORKDIR /app

# Install uv for fast package installation
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install common system-level dependencies (like GDAL)
# Make newest libraries available, debian is by default rather outdated aka "stable"
COPY util/unstable.sources /etc/apt/sources.list.d/unstable.sources
RUN apt-get update && apt-get remove -y libssl3 && \
    apt-get install -y \
    openssl-provider-legacy libexpat1 binutils libproj-dev libgdal-dev gdal-bin g++ && \
    rm -rf /var/lib/apt/lists/*

# Install Python GDAL bindings against the native GDAL version in this image
RUN GDAL_VERSION="$(gdal-config --version)" && \
    if [ "$GDAL_VERSION" = "3.12.4" ]; then \
      CXXFLAGS="-DABS=std::abs" uv pip install --system "GDAL==${GDAL_VERSION}"; \
    else \
      uv pip install --system "GDAL==${GDAL_VERSION}"; \
    fi && \
    python -c "from osgeo import gdal; print(gdal.VersionInfo('--version'))"

# Install common meta-dependencies required by the wrapper and other utils
COPY ./requirements.txt meta_requirements.txt
RUN uv pip install --system -r meta_requirements.txt

# Copy common wrapper scripts
COPY ./cwl_wrapper.py ./cwl_wrapper.py
COPY ./prefect_wrapper.py ./prefect_wrapper.py
COPY ./__init__.py .
