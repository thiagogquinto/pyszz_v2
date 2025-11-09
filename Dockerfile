FROM python:3.7-slim-buster

RUN echo "deb [trusted=yes] http://archive.debian.org/debian buster main contrib non-free" > /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://archive.debian.org/debian buster-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://archive.debian.org/debian-security buster/updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb [trusted=yes] http://archive.debian.org/debian buster-backports main contrib non-free" >> /etc/apt/sources.list && \
    apt-get -o Acquire::Check-Valid-Until=false update && \
    apt-get -y --no-install-recommends upgrade && \
    apt-get install -y --no-install-recommends \
        openjdk-11-jre-headless \
        wget libarchive13 libcurl4 libxml2 python-magic git && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/srcML/srcML/releases/download/v1.0.0/srcml_1.0.0-1_ubuntu18.04.deb && \
    dpkg -i srcml_1.0.0-1_ubuntu18.04.deb || apt-get -f install -y && \
    rm srcml_1.0.0-1_ubuntu18.04.deb


WORKDIR /usr/src/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY tools tools
RUN chmod +x tools/RefactoringMiner-2.0/bin/RefactoringMiner

COPY szz szz
COPY options.py .
COPY main.py .

ENTRYPOINT [ "python", "-u", "main.py" ]