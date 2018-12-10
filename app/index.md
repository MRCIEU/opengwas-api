---
title: "MR-Base API for GWAS summary data"
output:
  html_document:
    toc: true
    theme: united
---

---

This is an API which is used to pull down results from the [MR-Base](http://www.mrbase.org/) dataabase of GWAS summary data. It also has some helper functions pertaining to operations relating to LD calculations.

It is written using [FlaskRESTful](https://flask-restful.readthedocs.io/en/latest/). A mixture of `post` and `get` methods are implemented, and there are convenient functions for accessing the API in the [R/TwoSampleMR](https://github.com/MRCIEU/TwoSampleMR) R package. 

All results are json format.

---

## Check the status of the API

Gives some information on the version, and status of the services behind the API.

```
GET /status
```

e.g. [http://api.mrbase.org/status](http://api.mrbase.org/status)

---

## Authentication

Public datasets can be queried without any authentication, but some studies are only accessible by specific users. To authenticate we use Google OAuth2.0 access tokens. The token can be passed as header variable `X-Api-Token` in `POST` and `GET` requests. 

The easiest way to obtain an access token is through the [TwoSampleMR R](https://mrcieu.github.io/TwoSampleMR/#authentication) package using the `get_mrbase_access_token()` function. In R:

```r
devtools::install_github("MRCIEU/TwoSampleMR")
library(TwoSampleMR)
get_mrbase_access_token()
```

This will send you to a browser window in which you can enter your gmail credentials, and then upon authorisation it will generate a token.

---


## Available GWAS studies

### Get list of GWAS studies

```
GET /gwasinfo
```

e.g. [http://api.mrbase.org/gwasinfo](http://api.mrbase.org/gwasinfo)

Returns a large JSON object, with information pertaining to each study available in the database. Note, this only returns publicly available results unless a valid Google OAuth2.0 token is passed in the header.

e.g.

```bash
curl -i \
-H "Content-Type: application/json" \
-H "X-Api-Token: xxxxlongrandomhashxxxx" \
-X GET http://api.mrbase.org/gwasinfo
```

---

### Get info on particular GWAS studies

Find info on one or a few studies.

```
GET /gwasinfo/<mrbase-id,mrbase-id,mrbase-id>
```

e.g. [http://api.mrbase.org/gwasinfo/2](http://api.mrbase.org/gwasinfo/2) shows info on the GIANT BMI study 2015

e.g. [http://api.mrbase.org/gwasinfo/2,1001](http://api.mrbase.org/gwasinfo/2,1001) shows info on the above study and the SSGAC 2016 study on educational attainment.

---

The `POST` method can also be invoked. A complete list of studies can be obtained using

```
POST /gwasinfo
```

This can be accessed through `curl` e.g. using:

```bash
curl -i \
-H "Content-Type: application/json" \
-H "X-Api-Token: xxxxlongrandomhashxxxx" \
-X POST -d '
{
    'id': ['2','1001']
}
' http://api.mrbase.org/gwasinfo
```

Here we are providing the access token through the header, and posting a `json` document that contains the details of the query. Example:

If the header variable `X-Api-Token` is null then only public datasets are returned. If `id` is empty then the list of all datasets is returned.

---

## Query GWAS associations

### Extracting specific SNPs from specific datasets

Similar to the above, we have the following possible methods

```
GET /assoc/<mrbase-id>/<rsid>
```

e.g. [http://api.mrbase.org/assoc/2,1001/rs234](http://api.mrbase.org/assoc/2/rs234) obtained the `rs234` SNP from the BMI study.

e.g. [http://api.mrbase.org/assoc/2,1001/rs234](http://api.mrbase.org/assoc/2,1001/rs234) obtained the `rs234` SNP from two studies.


```
POST /assoc
```

```json
{
    'id': ['2','1001'],
    'rsid': ['rs234'],
    'proxies': 0,
    'r2': 0.8,
    'palindromes': 1,
    'align_alleles': 1,
    'maf_threshold': 0.3
}
```

`id` and `rsid` must be arrays of 1 or more. Default values for `proxies`, `palindromes`, `align_alleles`, `r2` and `maf_threshold` are shown. That is - by default LD proxies are not searched for if a variant is absent from a dataset, but if `proxies=1` then palindromic variants will be allowed if the MAF is <= 0.3. Minimum `r2` can be provided

---

### Extracting tophits from datasets

```
POST /tophits
```

```json
        'id': [<list of mrbase-ids>],
        'clump': 1,
        'pval': 5e-8,
        'r2': 0.001,
        'kb': 5000
```

Clumping is performed by default using arguments described below.

---

### PheWAS

Obtain the effects of a single variant on all available studies. Respects token in headers. Extracting on all studies is often faster than extracting on a large number of studies, so it may sometimes be preferable to do this first and filter on the results.

```
GET /phewas/<rsid>
```

Also available as `POST`

```
POST /phewas
```

with json:

```json
{
    'rsid': [list of rsids],
}
```

## LD operations

### Clumping

```
POST /clump
```

```json
{
    'rsid': [list of rsids],
    'pval': [list of p-values],
    'pthresh': 5e-8,
    'r2': 0.001,
    'kb': 5000
}
```

Performs clumping on a set of SNPs

---

### LD matrix

For a list of SNPs get the LD R values. These are presented relative to a specified reference allele.

```
POST /ldmatrix
```

```json
{
    'rsid': [list of rsids]
}
```

