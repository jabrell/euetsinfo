import os
import urllib.request
from datetime import UTC, datetime

import boto3

# Initialize the S3 client outside the handler for connection reuse
s3 = boto3.client("s3")


def lambda_handler(event, context):
    # The source URL
    url = (
        "https://dlsclimabi.blob.core.windows.net/public-data/eutlpublic/extracts/"
        "_all_extracts/registry_holdings/registry_holdings_daily.csv.gz"
    )

    # Fetch the target bucket from environment variables
    bucket_name = os.environ.get("S3_BUCKET_NAME")
    if not bucket_name:
        raise ValueError("S3_BUCKET_NAME environment variable is not set.")

    # Generate a timestamped key (e.g., 2026-06-17_registry_holdings.csv.gz)
    # This prevents you from overwriting yesterday's data, building a historical
    # archive.
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
    object_key = (
        f"downloads/registry_allowance_holdings/{date_str}_registry_holdings.csv.gz"
    )

    print(f"Starting download from {url}")

    try:
        # Open the URL and stream it directly to S3
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            print(f"Uploading directly to s3://{bucket_name}/{object_key}")

            # upload_fileobj automatically handles multipart uploads for larger files
            s3.upload_fileobj(response, bucket_name, object_key)

        print("Upload completed successfully.")

        return {
            "statusCode": 200,
            "body": f"Successfully archived daily snapshot to {object_key}",
        }

    except Exception as e:
        print(f"Failed to process daily download: {str(e)}")
        raise e
