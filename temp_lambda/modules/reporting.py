"""
Module for generating AWS access review reports in various formats.
"""

import csv
import io
import datetime


def generate_csv_report(findings):
    """
    Generate a CSV report from the collected findings.

    Args:
        findings: List of finding dictionaries

    Returns:
        A tuple of (csv_content_string, filename)
    """
    print("Generating CSV report...")

    # Create an in-memory CSV file
    csv_buffer = io.StringIO()
    csv_writer = csv.DictWriter(
        csv_buffer,
        fieldnames=[
            "id",
            "category",
            "severity",
            "resource_type",
            "resource_id",
            "description",
            "recommendation",
            "compliance",
            "detection_date",
        ],
    )

    # Write header and data
    csv_writer.writeheader()
    for finding in findings:
        csv_writer.writerow(finding)

    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"aws-access-review-{timestamp}.csv"

    return csv_buffer.getvalue(), filename


def upload_to_s3(s3_client, bucket, content, key, content_type="text/csv"):
    """
    Upload content to an S3 bucket.

    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        content: Content to upload
        key: S3 key (path) to upload to
        content_type: MIME type of the content

    Returns:
        S3 URL of the uploaded content
    """
    print(f"Uploading report to S3 bucket {bucket} with key {key}")

    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

        # Generate S3 URL
        s3_url = f"s3://{bucket}/{key}"
        print(f"Successfully uploaded to {s3_url}")

        return s3_url
    except Exception as e:
        error_msg = str(e)
        print(f"Error uploading to S3: {error_msg}")
        raise
