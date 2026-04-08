# argus

![Argus Lookup File](videos/argus_lookup_file.gif)

Fast IP lookups using MaxMind GeoIP2 and IP2Proxy databases.

## Prereqs

- Install uv from [https://docs.astral.sh/uv/getting-started/installation/](https://docs.astral.sh/uv/getting-started/installation/)
- Get a free MaxMind license key at [https://www.maxmind.com/en/geolite2/signup](https://www.maxmind.com/en/geolite2/signup)
- Get a free IP2Proxy download token at [https://www.ip2location.com/register](https://www.ip2location.com/register)

## Install

```bash
uv tool install git+https://github.com/bowenaguero/argus
```

## Setup

```bash
argus setup
```

## Usage

```bash
# Single IP
argus lookup 8.8.8.8

# From file
argus lookup -f ips.txt

# Filter results
argus lookup -f ips.txt -xc Germany -xa 15169

# Export to JSON/CSV
argus lookup -f ips.txt -o results.json
```

## Org Database Management

Import your organization's IP data so lookups automatically tag managed IPs with org info.

### Input Formats

**CSV** (must have `ip`, `org_id`, `platform` columns):

```csv
ip,org_id,platform
10.0.0.1,ACME,aws
10.0.0.2,ACME,azure
```

**JSON** (array of objects with `ip`, `org_id`, `platform` keys):

```json
[
  {"ip": "10.0.0.1", "org_id": "ACME", "platform": "aws"},
  {"ip": "10.0.0.2", "org_id": "ACME", "platform": "azure"}
]
```

### Commands

```bash
# Import from CSV or JSON (auto-detects by extension)
argus org import cloud_ips.csv

# Import with a custom database name
argus org import cloud_ips.json --name my_cloud

# Overwrite an existing database
argus org import cloud_ips.csv --force

# List all org databases
argus org list

# Remove an org database
argus org remove my_cloud
```

## Options

![Argus Help](images/argus_help.png)
