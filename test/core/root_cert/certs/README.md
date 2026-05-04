# BadSSL Test Certificates

This directory contains client certificates from [badssl.com](https://badssl.com/) used for testing SSL/TLS client certificate authentication.

## Files

- `no-password.pem` - Combined certificate and unencrypted private key
- `cert.crt` - Certificate only
- `key.key` - Private key only (unencrypted)
- `badssl.com-client.p12` - PKCS#12 format (password: `badssl.com`)
- `update-certs.sh` - Script to download and update certificates
- `gen.sh` - Original generation script (legacy)

## Updating Certificates

BadSSL periodically rotates their certificates. When tests start failing due to expired certificates, run:

```bash
cd test/core/root_cert/certs
./update-certs.sh
```

The script will:
1. Download the latest certificates from badssl.com
2. Extract and process them into the required formats
3. Verify the certificates are valid
4. Create a backup of existing certificates
5. Install the new certificates

After updating, run the certificate tests to verify:

```bash
cd dothttp
./run-tests.sh test/core/test_certs.py
```

If all tests pass, commit the changes:

```bash
git add test/core/root_cert/certs/
git commit -m "Update badssl certificates"
```

## Certificate Details

The certificates are downloaded from:
- PEM format: https://badssl.com/certs/badssl.com-client.pem
- P12 format: https://badssl.com/certs/badssl.com-client.p12

Password for encrypted keys: `badssl.com`

## Testing Endpoints

These certificates are used to test against:
- `https://client.badssl.com/` - Requires client certificate (returns 200 with cert, 400 without)
- `https://client-cert-missing.badssl.com/` - Should fail without client cert

## Troubleshooting

### Certificate Expired
If you see SSL certificate errors in tests, the certificates have likely expired. Run `./update-certs.sh` to get the latest ones.

### Connection Errors
If `update-certs.sh` fails to download certificates:
1. Check your internet connection
2. Verify badssl.com is accessible: `curl -I https://badssl.com/`
3. Try downloading manually from https://badssl.com/

### Test Failures After Update
If tests still fail after updating:
1. Verify certificate validity: `openssl x509 -in cert.crt -noout -dates`
2. Check badssl.com status: https://badssl.com/
3. Ensure Docker image has latest certificates (rebuild: `docker rmi dothttp-test-runner`)

## Automated Updates

Consider setting up a CI/CD job to periodically check certificate expiration:

```bash
# Check certificate expiration (30 days warning)
openssl x509 -in cert.crt -noout -checkend 2592000
```

Exit code 0 = still valid, 1 = expires within 30 days or already expired.
