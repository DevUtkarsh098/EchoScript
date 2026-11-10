# Terraform state bootstrap

Run only in the approved new AWS account and region. This creates one S3 state bucket and one DynamoDB lock table. The bucket is private, versioned, AES-256 encrypted, rejects non-TLS requests, and cannot be destroyed by Terraform. The lock table uses on-demand billing, server-side encryption, and cannot be destroyed by Terraform.

## First-time bootstrap

1. Confirm the active CLI profile is the non-root `echoscript-deploy` profile for the intended account.
2. Initialize locally: `AWS_PROFILE=echoscript-deploy AWS_REGION=us-west-2 terraform init`.
3. Review the plan: `AWS_PROFILE=echoscript-deploy AWS_REGION=us-west-2 terraform plan -input=false`.
4. After explicit owner approval, apply the plan: `AWS_PROFILE=echoscript-deploy AWS_REGION=us-west-2 terraform apply`.
5. Get the bucket/table names from the Terraform outputs.
6. Add `backend "s3" {}` inside the `terraform` block in `versions.tf`, then migrate this bootstrap state into S3 using `terraform init -migrate-state -backend-config="bucket=STATE_BUCKET_NAME" -backend-config="key=echoscript/bootstrap/terraform.tfstate" -backend-config="region=us-west-2" -backend-config="encrypt=true" -backend-config="dynamodb_table=echoscript-terraform-lock"`. Confirm the migration prompt.

The application root uses a separate state key in the same bucket. Do not delete the state bucket or lock table as ordinary cleanup.
