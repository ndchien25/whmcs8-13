# eNom response overrides

`config.json` is read again for every request. After the volume has been
created once, editing this directory does not require a container restart or
recreation.

Rules are matched case-insensitively against eNom's `Command` query/form
parameter. An absent rule, or a rule with `"enabled": false`, is passed through
to eNom. An enabled rule is returned locally and eNom is not contacted.

Example:

```json
{
  "apis": {
    "Check": {
      "enabled": true,
      "status_code": 200,
      "headers": {
        "content-type": "text/xml; charset=utf-8"
      },
      "body_file": "responses/check.xml"
    }
  }
}
```

`body` can be used instead of `body_file`. Response files must be located
inside this directory. A malformed config or response rule fails open and
sends the request to eNom.
