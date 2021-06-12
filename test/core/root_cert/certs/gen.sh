# to upgrade
# download latest certificate from https://badssl.com/download/
# and run this script to update certs
filename=badssl.com-client.p12
password=badssl.com

# gen cert & key
openssl pkcs12 -in $filename -out cert.crt -nodes -passin pass:$password
openssl pkcs12 -in $filename -out key.key -nodes -nocerts -passin pass:$password

# gen cert & key in same file
openssl pkcs12 -in $filename -out no-password.pem -nodes -passin pass:$password
