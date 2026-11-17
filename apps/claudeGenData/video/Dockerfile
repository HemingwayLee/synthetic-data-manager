FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

# ffmpeg (with libass) to mux and burn subtitles; Japanese fonts for the browser and subtitles.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir playwright==1.55.0

WORKDIR /video
ENTRYPOINT ["python", "generate.py"]
