# State bootstrap module

`enabled` defaults to `false`. Enabled configuration describes a private S3
bucket with all four public-access blocks, enforced bucket ownership,
versioning, SSE-KMS and blocked SSE-C uploads. The KMS key rotates automatically
and has a 30-day deletion window. Key and bucket have `prevent_destroy` guards;
`force_destroy` is false. A TLS-only bucket
policy denies insecure requests. Two further deny statements require every
upload to send `aws:kms` and this key's exact ARN, preventing encryption headers
from overriding the bucket default with SSE-S3 or another key. The root backend
remains local.

Enabled inputs include a globally unique `bucket_name`, explicit `account_id`,
and existing `key_admin_role_name` and `state_operator_role_name`. The future
bootstrap actor must be the named administrator or independently authorized
to retain key administration; key-policy lockout safety is not bypassed. Roles
and their identity/trust prerequisites are not created or discovered here.
No concrete account, role or usable bucket is recommended by the mock fixtures.

The operator's inline IAM policy scopes S3 listing and object access to
`lab/foundation/terraform.tfstate` and its `.tflock` object, or the separate
`dev/` keys. State allows Get/Put; only the lock allows DeleteObject. Workspace
deletion and state deletion are excluded. KMS usage names the exact key ARN and is restricted to S3 in the
selected region and this bucket's encryption context. Bucket Keys are enabled.
The KMS resource-policy `Resource = "*"` means the attached key only; principals
are explicit and actions are enumerated. The bucket policy's wildcard is a
TLS **Deny**, never a grant.

These scoped grants are not a permissions boundary for existing roles: other
policies on those roles require separate review. The OpenTofu deletion guards
do not prevent an authorized administrator acting outside OpenTofu.

`backend_configuration` outputs future encrypted S3 coordinates with
`use_lockfile = true`; output alone does not configure a backend, create a
bucket or migrate state. There is no DynamoDB locking table. Native S3 locking
and version recovery have not been exercised against AWS. Existing-object
version recovery needs separately reviewed permissions and procedures.

The foundation state bucket cannot bootstrap itself. Any future authorized
operator must first manage this stack with separate protected local/bootstrap
state, then review migration and retain that bootstrap state securely. The
repository task interface prohibits these operations.

References: [OpenTofu S3 backend](https://opentofu.org/docs/language/settings/backends/s3/),
[AWS KMS key-policy resource semantics](https://docs.aws.amazon.com/kms/latest/developerguide/key-policy-overview.html),
[AWS SSE-KMS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html),
[S3 default encryption and request overrides](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html).
