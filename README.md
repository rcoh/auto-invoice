## Generate Certificate for Xero
openssl genrsa -out privatekey.pem 1024
openssl req -new -x509 -key privatekey.pem -out publickey.cer -days 1825
openssl pkcs12 -export -out public_privatekey.pfx -inkey privatekey.pem -in publickey.cer

## Generate App password for Gmail
https://security.google.com/settings/security/apppasswords