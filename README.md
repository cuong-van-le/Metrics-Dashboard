# Roxxane

Roxxane is a data ingestion pipeline designed to collect system metrics and stream them to AWS Kinesis Firehose for processing and storage. The system automatically provisions AWS infrastructure, transforms data in real-time, and stores it in S3 with dynamic partitioning for efficient querying.

## Architecture Overview

The system follows a modular architecture with clear separation of concerns across infrastructure provisioning, data collection, transformation, and delivery.

### Core Components

**Infrastructure as Code (IaC)**
The `iac/` module handles all AWS resource provisioning through a declarative approach. Resources are managed through a base `Resource` class that implements a consistent ensure pattern - checking for existence, handling updates, or creating new resources as needed. The `InfrastructureOrchestrator` manages dependencies between resources using topological sorting, ensuring resources are created in the correct order.

**Metrics Collection**
The `metrics/` module provides system-level metric collection using psutil. It collects CPU, RAM, network, and disk metrics at configurable intervals. The `MetricsCollector` runs in a background thread and supports callback-based delivery, allowing flexible integration with different delivery mechanisms.

**Data Pipeline**
The `pipeline/` module implements the ingestion layer. The `Ingestion` class bridges metrics collection with Firehose delivery, converting metrics to JSON and sending them via the Firehose API. It implements the `Pipeline` abstract interface for extensibility.

**Transformation**
The `transform/` module contains the Lambda function that processes records in transit. It enriches records with timestamp information, extracts partition keys for dynamic partitioning, and converts data to Parquet format for efficient storage and querying.

**Configuration Management**
The `config/` module centralizes configuration through environment variables. It validates required settings, manages optional parameters, and persists state between runs. The `State` class tracks ARNs of created resources, enabling idempotent operations.

### Data Flow

1. Metrics are collected locally by the `MetricsCollector` at regular intervals (default 3 seconds)
2. Each metric is converted to a dictionary and sent to Kinesis Firehose via `put_record`
3. Firehose buffers records and invokes the Lambda transformation function
4. The Lambda function enriches records with partition keys (year, month, day, hour) based on timestamp
5. Transformed records are written to S3 with dynamic partitioning enabled
6. Data is stored in Parquet format for efficient compression and querying
7. AWS Glue Crawler (configured separately) discovers partitions and updates the catalog

### Infrastructure Dependencies

The orchestrator manages the following dependency graph:
- Bucket and Lambda can be created in parallel (no dependencies)
- Role depends on both Bucket and Lambda (needs their ARNs)
- Firehose depends on Role, Bucket, and Lambda (needs all ARNs)

This ensures resources are provisioned in the correct order, with parallel execution where possible.

## Setup

### Prerequisites

- Python 3.10 or higher
- AWS account with appropriate permissions
- AWS CLI configured with credentials

### Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd roxxane
pip install -r requirements.txt
```

For development, install additional testing dependencies:

```bash
pip install -r requirements-dev.txt
```

### Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

**Required Variables:**
- `DELIVERY_STREAM_NAME` - Name for the Kinesis Firehose delivery stream
- `PREFIX` - S3 prefix for data storage (e.g., `analytics/`)
- `BUFFERING_SIZE` - Buffer size in MB (integer, e.g., `5`)
- `BUFFERING_TIME` - Buffer time in seconds (integer, e.g., `300`)
- `REGION_NAME` - AWS region (e.g., `eu-central-1`)
- `ROLE_NAME` - IAM role name for Firehose
- `BUCKET_NAME` - S3 bucket name (must be globally unique)
- `LAMBDA_FUNCTION_NAME` - Lambda function name
- `LAMBDA_RUNTIME` - Lambda runtime (e.g., `python3.12`)
- `LAMBDA_HANDLER` - Lambda handler (e.g., `app.handler`)
- `LAMBDA_TIMEOUT` - Lambda timeout in seconds (integer)
- `LAMBDA_MEMORY_MB` - Lambda memory in MB (integer)

**Optional Variables:**
- `GLUE_DATABASE_NAME` - Glue database name for Parquet schema
- `GLUE_TABLE_NAME` - Glue table name for Parquet schema
- `LOG_LEVEL` - Logging level (default: `INFO`)

### Initial Deployment

Run the main script to provision infrastructure:

```bash
python main.py --update-env
```

This will:
1. Create or verify the S3 bucket
2. Package and deploy the Lambda function
3. Create IAM roles with appropriate permissions
4. Create the Kinesis Firehose delivery stream
5. Update `.env` with resource ARNs
6. Save state to `iac/state.json`

The `--update-env` flag automatically updates your `.env` file with the ARNs of created resources. Without this flag, ARNs are only saved to `iac/state.json`.

### Glue Crawler Setup

The system includes CloudFormation templates for setting up AWS Glue resources, but you need to deploy and configure the crawler separately. The crawler is responsible for discovering partitions in your S3 data and updating the Glue catalog.

Deploy the Glue resources using the CloudFormation templates in `.aws/cloudformation/`:

1. Deploy the database: `.aws/cloudformation/glue-database.yaml`
2. Deploy the table: `.aws/cloudformation/glue-table.yaml`
3. Deploy the crawler: `.aws/cloudformation/glue-crawler.yaml`

Configure the crawler schedule according to your needs. The default is hourly, but you can set it to `NONE` for manual runs only.

## Usage

### Starting the Ingestion Pipeline

Once infrastructure is provisioned, start the ingestion process:

```bash
python main.py
```

This starts the metrics collector and begins sending data to Firehose. The process runs until interrupted with Ctrl+C.

### Updating Lambda Code

If you modify the transformation function in `transform/app.py`, redeploy:

```bash
python main.py --update-env
```

The system detects existing Lambda functions and updates their code automatically.

### Monitoring

Check CloudWatch Logs for:
- Firehose delivery stream logs: `/aws/kinesis_firehose/<stream-name>`
- Lambda function logs: `/aws/lambda/<function-name>`

Monitor S3 bucket metrics to verify data is being written successfully.

## Testing

The test suite is organized by test type. Note that the test suite was generated with AI assistance to ensure comprehensive coverage:

- **Unit tests** - Mock AWS services, no credentials required
- **Integration tests** - Require AWS credentials and real resources
- **Property-based tests** - Use Hypothesis for generative testing
- **Performance tests** - Benchmark critical paths

Run unit tests (no AWS credentials needed):

```bash
pytest tests/ -m unit
```

Run all tests except integration (requires AWS credentials):

```bash
pytest tests/ -m "not integration"
```

The CI/CD pipeline runs unit tests automatically on push and pull requests.

## Project Structure

```
roxxane/
├── [config/](config/)           # Configuration management and environment handling
├── [iac/](iac/)                # Infrastructure as Code - AWS resource provisioning
├── [metrics/](metrics/)         # System metrics collection
├── [pipeline/](pipeline/)      # Data ingestion and delivery
├── [transform/](transform/)    # Lambda transformation function
├── [tests/](tests/)            # Test suite (AI-generated)
├── [.aws/cloudformation/](.aws/cloudformation/)  # CloudFormation templates for Glue resources
├── [scripts/](scripts/)         # Utility scripts
├── [quicksight/](quicksight/)   # QuickSight dashboard examples and documentation
└── main.py                     # Application entry point
```

### Directory Descriptions

- **[config/](config/)** - Handles environment variable loading, configuration validation, and state management. Contains the main configuration dataclasses and environment updater utilities.

- **[iac/](iac/)** - Infrastructure as Code module responsible for provisioning AWS resources. Implements the resource orchestration pattern with dependency management, retry logic, and idempotent operations.

- **[metrics/](metrics/)** - System metrics collection using psutil. Provides CPU, RAM, network, and disk metric collection with configurable intervals and callback-based delivery.

- **[pipeline/](pipeline/)** - Data ingestion pipeline that bridges metrics collection with Firehose delivery. Implements the abstract Pipeline interface for extensibility.

- **[transform/](transform/)** - Lambda function code that processes records in transit. Enriches data with timestamps, extracts partition keys, and handles Parquet conversion.

- **[tests/](tests/)** - Comprehensive test suite covering unit, integration, property-based, and performance tests. Test suite was generated with AI assistance.

- **[.aws/cloudformation/](.aws/cloudformation/)** - CloudFormation templates for AWS Glue resources including database, table, and crawler definitions.

- **[scripts/](scripts/)** - Utility scripts for manual Lambda packaging and other development tasks.

- **[quicksight/](quicksight/)** - QuickSight dashboard examples, documentation, and visualizations showing how to analyze the collected metrics data.

## Design Decisions

**Idempotent Operations**
All infrastructure operations are idempotent. Running the deployment multiple times produces the same result - existing resources are detected and updated rather than recreated.

**Dependency Management**
The orchestrator uses topological sorting to resolve dependencies automatically. This eliminates manual ordering and enables parallel creation where possible.

**State Persistence**
Resource ARNs are persisted to `iac/state.json` to enable idempotent operations and avoid redundant API calls. The state file is versioned to support future migrations.

**Dynamic Partitioning**
Firehose is configured with dynamic partitioning based on timestamp. This enables efficient querying by time ranges without scanning entire datasets.

**Parquet Format**
Data is stored in Parquet format with Snappy compression. This provides excellent compression ratios and columnar storage benefits for analytics workloads.

**Retry Logic**
IAM role propagation delays are handled with automatic retries. The system detects common transient errors and retries with exponential backoff.

## Troubleshooting

**Lambda function not found**
Ensure the Lambda function was created successfully. Check `iac/state.json` for the `LAMBDA_ARN`. If missing, run `python main.py --update-env` again.

**Firehose stream stuck in CREATING**
This usually indicates IAM permission issues. Verify the Firehose role has permissions to write to S3 and invoke the Lambda function. Check CloudWatch Logs for detailed error messages.

**No data in S3**
Verify the Firehose stream status is ACTIVE. Check CloudWatch metrics for delivery errors. Ensure the Lambda function is returning records with `result: "Ok"`.

**Partition discovery not working**
Ensure the Glue crawler is configured and running. Verify the crawler has permissions to read from the S3 bucket. Check that the table schema matches the data structure.

## Security

This project takes security seriously. We use automated security scanning and dependency management:

- **Dependabot** - Automatically checks for and updates vulnerable dependencies
- **CodeQL** - Static code analysis to identify security vulnerabilities
- **Bandit** - Python-specific security linting
- **Safety** - Checks dependencies against known vulnerability databases

Security issues can be reported privately by opening a security advisory in the GitHub repository.

## Contributing

Contributions are welcome. Please ensure:

- All tests pass (`pytest tests/ -m unit`)
- Code follows the project's style guidelines
- New features include appropriate tests
- Documentation is updated as needed

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
