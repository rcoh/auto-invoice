## Autoinvoice

This project will automatically generate a report from Toggl then create an invoice in Xero. Setup:

1. mkdir ~/.invoice
2. touch ~/.invoice/config.ini
3. Geneate certificates for Xero

```
cd ~/.invoice
openssl genrsa -out privatekey.pem 1024
openssl req -new -x509 -key privatekey.pem -out publickey.cer -days 1825
openssl pkcs12 -export -out public_privatekey.pfx -inkey privatekey.pem -in publickey.cer
```

4. Setup a private app on Xero: https://app.xero.com/Application

5. Generate App password for Gmail (if you use 2-factor)
https://security.google.com/settings/security/apppasswords

6. Setup virtual env:

```
pip install inenv
inenv init default
inenv default
```

7. Configure:

```
python main.py configure
```

8. Add a client:

```
python main.py add_client
```

9. Send an invoice! It will find clients that need to be invoiced, and send them out.

```
python main.py send_invoice
```

