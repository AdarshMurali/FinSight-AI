# GitHub Actions AWS Access — OIDC Federation

No long-lived AWS access keys are stored in GitHub. Instead, GitHub Actions
assumes a scoped IAM role for the duration of each CD job, via OpenID Connect
federation. Credentials are minted fresh per job run and expire shortly after.

## What's set up (AWS account 301276846405, ap-south-1)

1. **OIDC Identity Provider**: `token.actions.githubusercontent.com`
   (`aws iam create-open-id-connect-provider`, one-time, thumbprint
   `6938fd4d98bab03faadb97b34396831e3780aea1` — GitHub's documented root CA
   thumbprint).

2. **IAM Role**: `finsight-github-actions-cd`
   - Trust policy (`github-actions-trust-policy.json`): only allows
     `sts:AssumeRoleWithWebIdentity` from a token whose `sub` claim matches
     `repo:AdarshMurali/FinSight-AI:environment:*` — i.e. only jobs in *this*
     repo that target a GitHub Environment (which `cd.yml`'s deploy jobs
     always do) can assume it. A plain push-triggered job with no
     `environment:` set (like `ci.yml`, which never needs AWS at all) cannot.
   - Permissions policy (`github-actions-cd-permissions.json`):
     - `ssm:SendCommand` scoped to exactly the two EC2 instances (backend
       `i-0d5332841d8f8da41`, Flink `i-06df445415d082798`) and the
       `AWS-RunShellScript` document
     - `ssm:GetCommandInvocation` — `Resource: "*"` is not a scoping choice
       here, it's an AWS constraint: this action has no resource-level
       permission support at all (confirmed live 2026-07-17 when the first
       real CD run hit `AccessDeniedException` with an instance-scoped
       resource — AWS's own doc for this action says `Resource: "*"` is
       required, since invocation status/output isn't addressable by an
       instance or command ARN at the IAM layer)
     - `ec2:StartInstances`/`StopInstances` scoped to the Flink EC2 only (needed
       so CD can start it if it's off outside market hours, then stop it again
       if CD is what started it)
     - `ec2:DescribeInstances`/`DescribeInstanceStatus` — `Resource: "*"`
       is not a scoping choice here either, it's the same AWS constraint:
       these are list-type actions that don't support resource-level IAM
       permissions at all.

## Recreating this from scratch

```bash
aws iam create-open-id-connect-provider --profile lavanya \
  --url "https://token.actions.githubusercontent.com" \
  --client-id-list "sts.amazonaws.com" \
  --thumbprint-list "6938fd4d98bab03faadb97b34396831e3780aea1"

aws iam create-role --profile lavanya \
  --role-name finsight-github-actions-cd \
  --assume-role-policy-document file://aws/iam/github-actions-trust-policy.json

aws iam put-role-policy --profile lavanya \
  --role-name finsight-github-actions-cd \
  --policy-name finsight-cd-deploy-permissions \
  --policy-document file://aws/iam/github-actions-cd-permissions.json
```

Then set the resulting role ARN as a GitHub repo variable `AWS_CD_ROLE_ARN`
(not a secret — ARNs aren't sensitive) for `cd.yml` to reference via
`aws-actions/configure-aws-credentials`.
