# EPB Usage Exporter

You can use this to export your electricity usage from your EPB account

#### How to run

```
# build the local container
docker build -t epb:latest .

# running for the past month using access token
docker run -e ACCESS_TOKEN=<your-access-token> -it --rm epb:latest

# running for the past month using access token
docker run -e ACCESS_TOKEN=<your-access-token> -e FROM_YYYY=<start-year> -e FROM_MM=<start-month> -e TO_YYYY=<end-year> -e TO_MM=<end-month> -v ${PWD}/data:/app/data -it --rm epb:latest

# running for the past month
docker run -e USERNAME=<your-username> -e PASSWORD=<your-password> -it --rm epb:latest

# running for the past month
docker run -e USERNAME=<your-username> -e PASSWORD=<your-password> -e FROM_YYYY=<start-year> -e FROM_MM=<start-month> -e TO_YYYY=<end-year> -e TO_MM=<end-month> -v ${PWD}/data:/app/data -it --rm epb:latest
```

