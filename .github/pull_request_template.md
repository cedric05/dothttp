Any new Feature should handle all of below

- http2har (export to all programming languages using httpsnippet or request sharing)
- har2http (swagger3 import, swagger2 import, curl import)
- postman2http (postman3 postman2 import)
- http2postman (export http file to postman request collection)
- http2curl (mirror, to check syntax or most scenarios)

are expected to work by default for any new feature. here is the checklist

- [ ] check request executed properly
    - [ ] test case
- [ ] check har is generated properly and test case
    - [ ] test case
- [ ] check postman collection export of that use is generated properly
    - [ ] test case
- [ ] check with this new feature, postman import (few left out) can be bought back
    - [ ] test case
- [ ] check curl is generated like expected
    - [ ] test case