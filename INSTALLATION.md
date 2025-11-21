# TaxPulse PH Pack - Installation & Integration Guide

Complete guide for integrating TaxPulse PH Pack with your Odoo 18.0 and Supabase stack.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Odoo Installation](#odoo-installation)
3. [Supabase Setup](#supabase-setup)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [Apache Superset Integration](#apache-superset-integration)

---

## Prerequisites

### Required Software

- **Odoo CE 18.0** or higher
- **Python 3.11+**
- **PostgreSQL 15+**
- **Supabase Account** (project: xkxyvboeubffxxbebsll)
- **Git**

### Environment Variables

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Supabase Configuration
export SUPABASE_URL="https://xkxyvboeubffxxbebsll.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
export SUPABASE_ANON_KEY="your-anon-key"

# Odoo Configuration (optional)
export ODOO_API_KEY="your-odoo-admin-password"
```

Reload your shell:

```bash
source ~/.zshrc  # or source ~/.bashrc
```

---

## Odoo Installation

### Step 1: Clone the Repository

```bash
cd /path/to/odoo/addons
git clone https://github.com/jgtolentino/TaxPulse-PH-Pack.git taxpulse_ph_pack
```

### Step 2: Install Python Dependencies

```bash
cd taxpulse_ph_pack
pip install -r requirements.txt
```

### Step 3: Update Odoo Module List

1. Restart Odoo server:

```bash
sudo systemctl restart odoo
# OR
/path/to/odoo-bin -c /etc/odoo/odoo.conf
```

2. Go to Odoo web interface: **Apps** → **Update Apps List**

### Step 4: Install the Module

1. Search for "TaxPulse PH Pack"
2. Click **Install**
3. Wait for installation to complete (agencies will be created automatically)

### Step 5: Verify Installation

Check that 8 agencies were created:

```bash
# Via Odoo web interface
Go to: Accounting > Configuration > TaxPulse > Agencies

# Via XML-RPC
python -c "
import xmlrpc.client
url = 'https://erp.insightpulseai.net'
db = 'production'
username = 'admin'
password = 'your-password'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
agencies = models.execute_kw(db, uid, password, 'taxpulse.agency', 'search_read', [[]], {'fields': ['code', 'name']})
print(f'Found {len(agencies)} agencies:', agencies)
"
```

Expected output:

```
Found 8 agencies: [
    {'code': 'RIM', 'name': 'RIM Agency'},
    {'code': 'CKVC', 'name': 'CKVC Agency'},
    {'code': 'BOM', 'name': 'BOM Agency'},
    {'code': 'JPAL', 'name': 'JPAL Agency'},
    {'code': 'JLI', 'name': 'JLI Agency'},
    {'code': 'JAP', 'name': 'JAP Agency'},
    {'code': 'LAS', 'name': 'LAS Agency'},
    {'code': 'RMQB', 'name': 'RMQB Agency'}
]
```

---

## Supabase Setup

### Step 1: Apply Schema Migrations

```bash
cd /path/to/taxpulse_ph_pack

# Connection URL (use direct port 5432 for migrations)
POSTGRES_URL="postgresql://postgres.xkxyvboeubffxxbebsll:$SUPABASE_DB_PASSWORD@aws-1-us-east-1.pooler.supabase.com:5432/postgres"

# Apply migrations
psql "$POSTGRES_URL" -f supabase/001_create_bir_tables.sql
psql "$POSTGRES_URL" -f supabase/002_rpc_functions.sql
```

### Step 2: Verify Schema

Check that tables and RPC functions were created:

```bash
psql "$POSTGRES_URL" -c "
SELECT schemaname, tablename, tableowner, rowsecurity
FROM pg_tables
WHERE schemaname = 'bir'
ORDER BY tablename;
"
```

Expected output:

```
 schemaname |      tablename       | tableowner | rowsecurity
------------+----------------------+------------+-------------
 bir        | agencies             | postgres   | t
 bir        | form_1601c           | postgres   | t
 bir        | form_1702rt          | postgres   | t
 bir        | form_2550q           | postgres   | t
 bir        | user_agency_access   | postgres   | t
```

Check RPC functions:

```bash
psql "$POSTGRES_URL" -c "
SELECT proname, proargnames
FROM pg_proc
WHERE pronamespace = 'bir'::regnamespace
ORDER BY proname;
"
```

### Step 3: Verify RLS Policies

```bash
psql "$POSTGRES_URL" -c "
SELECT schemaname, tablename, policyname, permissive, roles, cmd
FROM pg_policies
WHERE schemaname = 'bir'
ORDER BY tablename, policyname;
"
```

---

## Configuration

### Step 1: Configure Agency Details

Go to **Accounting > Configuration > TaxPulse > Agencies** and update:

1. **TIN** (Tax Identification Number)
2. **RDO Code** (Revenue District Office)
3. **Line of Business**
4. **Address**

### Step 2: Map Analytic Accounts

For each agency:

1. Go to **Accounting > Configuration > Analytic Accounting > Analytic Accounts**
2. Create or select analytic account for each agency
3. Link to agency in **TaxPulse > Agencies**

Example:

```
Agency: RIM → Analytic Account: RIM Operations
Agency: CKVC → Analytic Account: CKVC Operations
...
```

### Step 3: Configure User Access (Supabase)

Grant users access to specific agencies:

```sql
-- Grant Jake Tolentino access to all agencies
INSERT INTO bir.user_agency_access (user_id, agency_code, role)
SELECT auth.uid(), code, 'admin'
FROM bir.agencies
WHERE code IN ('RIM', 'CKVC', 'BOM', 'JPAL', 'JLI', 'JAP', 'LAS', 'RMQB')
ON CONFLICT (user_id, agency_code) DO NOTHING;
```

---

## Testing

### Test 1: Create BIR Form 1601-C

```python
# Via Odoo Python console or external script
import xmlrpc.client

url = 'https://erp.insightpulseai.net'
db = 'production'
username = 'admin'
password = 'your-password'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Create BIR 1601-C form
form_id = models.execute_kw(db, uid, password, 'bir.1601c', 'create', [{
    'agency_id': 1,  # RIM agency (adjust ID)
    'period_start': '2025-10-01',
    'period_end': '2025-10-31',
    'compensation_tax': 50000.00,
    'final_tax': 20000.00,
}])

print(f'Created BIR 1601-C form ID: {form_id}')

# Confirm the form
models.execute_kw(db, uid, password, 'bir.1601c', 'action_confirm', [[form_id]])

# Post the form (will trigger Supabase sync)
models.execute_kw(db, uid, password, 'bir.1601c', 'action_post', [[form_id]])
```

### Test 2: Verify Supabase Sync

```bash
# Query Supabase to check if form was synced
curl -X POST "$SUPABASE_URL/rest/v1/rpc/get_bir_dashboard_stats" \
  -H "apikey: $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Authorization: Bearer $SUPABASE_SERVICE_ROLE_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_start_date": "2025-10-01", "p_end_date": "2025-10-31"}' | jq
```

Expected output:

```json
[
  {
    "form_type": "1601-C",
    "agency_code": "RIM",
    "count_forms": 1,
    "total_tax": 70000.00,
    "avg_tax": 70000.00,
    "period_start": "2025-10-01",
    "period_end": "2025-10-31"
  }
]
```

### Test 3: Bulk Sync

```python
# Sync all posted forms to Supabase
sync_model = env['taxpulse.supabase.sync']
results = sync_model.bulk_sync_all()

print(results)
# Output:
# {
#   'bir_1601c': {'success': 5, 'failed': 0},
#   'bir_2550q': {'success': 2, 'failed': 0},
#   'bir_1702rt': {'success': 1, 'failed': 0}
# }
```

---

## Troubleshooting

### Issue: "Supabase service role key not configured"

**Solution**:

```bash
# Verify environment variable is set
echo $SUPABASE_SERVICE_ROLE_KEY

# If empty, add to ~/.zshrc and reload
export SUPABASE_SERVICE_ROLE_KEY="your-key-here"
source ~/.zshrc

# Restart Odoo server
sudo systemctl restart odoo
```

### Issue: "Remote table 'bir.form_1601c' not found"

**Solution**: Apply Supabase migrations

```bash
psql "$POSTGRES_URL" -f supabase/001_create_bir_tables.sql
psql "$POSTGRES_URL" -f supabase/002_rpc_functions.sql
```

### Issue: "Access denied" when syncing to Supabase

**Solution**: Check RLS policies

```sql
-- Verify service role bypass policy exists
SELECT policyname, cmd
FROM pg_policies
WHERE schemaname = 'bir'
AND policyname LIKE '%service_role%';

-- If missing, recreate policies from migration file
```

### Issue: Agencies not created on installation

**Solution**: Manually run post-installation hook

```python
# Via Odoo shell
env = api.Environment(cr, SUPERUSER_ID, {})

agencies = [
    {"code": "RIM", "name": "RIM Agency"},
    {"code": "CKVC", "name": "CKVC Agency"},
    {"code": "BOM", "name": "BOM Agency"},
    {"code": "JPAL", "name": "JPAL Agency"},
    {"code": "JLI", "name": "JLI Agency"},
    {"code": "JAP", "name": "JAP Agency"},
    {"code": "LAS", "name": "LAS Agency"},
    {"code": "RMQB", "name": "RMQB Agency"},
]

for agency_data in agencies:
    env['taxpulse.agency'].create(agency_data)

env.cr.commit()
```

---

## Apache Superset Integration

### Step 1: Add Supabase as Data Source

1. Go to **Superset > Data > Databases > + Database**
2. Select **PostgreSQL**
3. Configure connection:

```
Host: aws-1-us-east-1.pooler.supabase.com
Port: 6543  # Use pooler for production
Database: postgres
Username: postgres.xkxyvboeubffxxbebsll
Password: [SUPABASE_DB_PASSWORD]
```

### Step 2: Create SQL Lab Queries

Example queries:

```sql
-- Monthly withholding tax by agency
SELECT
    agency_code,
    month,
    year,
    SUM(compensation_tax) as total_compensation,
    SUM(final_tax) as total_final,
    SUM(total_tax_withheld) as total_tax
FROM bir.form_1601c
WHERE state = 'posted'
AND year = '2025'
GROUP BY agency_code, month, year
ORDER BY agency_code, year, month;

-- Quarterly VAT by agency
SELECT
    agency_code,
    quarter,
    year,
    SUM(output_vat) as total_output,
    SUM(input_vat) as total_input,
    SUM(vat_payable) as total_vat_payable
FROM bir.form_2550q
WHERE state = 'posted'
AND year = '2025'
GROUP BY agency_code, quarter, year
ORDER BY agency_code, year, quarter;
```

### Step 3: Create Dashboards

Use `get_bir_dashboard_stats()` RPC function for aggregated data:

```sql
-- Dashboard query (via Superset)
SELECT * FROM get_bir_dashboard_stats('2025-01-01', '2025-12-31')
ORDER BY form_type, agency_code;
```

---

## Next Steps

1. **Configure BIR Form Templates**: Customize PDF report templates in `reports/`
2. **Set up Automated Workflows**: Schedule monthly/quarterly form generation
3. **Integrate with n8n**: Create automation workflows for BIR filing reminders
4. **Monitor Sync Health**: Set up Supabase Edge Functions for monitoring
5. **Train Users**: Conduct training sessions on BIR form creation and workflows

---

## Support

- **GitHub Issues**: https://github.com/jgtolentino/TaxPulse-PH-Pack/issues
- **Documentation**: README.rst
- **Email**: jgtolentino@example.com
