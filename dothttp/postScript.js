// as this is embedded script, i couldn't include as npm package
// isEqual is copied or picked from https://github.com/NickGard/tiny-isequal/ project
// isEqual is licenced with MIT https://github.com/NickGard/tiny-isequal/blob/master/LICENSE
// don't remove this, while distributing

function isEqual() {
    var toString = Object.prototype.toString,
        getPrototypeOf = Object.getPrototypeOf,
        getOwnProperties = Object.getOwnPropertySymbols
            ? function (c) {
                return Object.keys(c).concat(Object.getOwnPropertySymbols(c));
            }
            : Object.keys;

    function checkEquality(a, b, refs) {
        var aElements,
            bElements,
            element,
            aType = toString.call(a),
            bType = toString.call(b);

        // trivial case: primitives and referentially equal objects
        if (a === b) return true;

        // if both are null/undefined, the above check would have returned true
        if (a == null || b == null) return false;

        // check to see if we've seen this reference before; if yes, return true
        if (refs.indexOf(a) > -1 && refs.indexOf(b) > -1) return true;

        // save results for circular checks
        refs.push(a, b);

        if (aType != bType) return false; // not the same type of objects

        // for non-null objects, check all custom properties
        aElements = getOwnProperties(a);
        bElements = getOwnProperties(b);
        if (
            aElements.length != bElements.length ||
            aElements.some(function (key) {
                return !checkEquality(a[key], b[key], refs);
            })
        ) {
            return false;
        }

        switch (aType.slice(8, -1)) {
            case "Symbol":
                return a.valueOf() == b.valueOf();
            case "Date":
            case "Number":
                return +a == +b || (+a != +a && +b != +b); // convert Dates to ms, check for NaN
            case "RegExp":
            case "Function":
            case "String":
            case "Boolean":
                return "" + a == "" + b;
            case "Set":
            case "Map": {
                aElements = a.entries();
                bElements = b.entries();
                do {
                    element = aElements.next();
                    if (!checkEquality(element.value, bElements.next().value, refs)) {
                        return false;
                    }
                } while (!element.done);
                return true;
            }
            case "ArrayBuffer":
                (a = new Uint8Array(a)), (b = new Uint8Array(b)); // fall through to be handled as an Array
            case "DataView":
                (a = new Uint8Array(a.buffer)), (b = new Uint8Array(b.buffer)); // fall through to be handled as an Array
            case "Float32Array":
            case "Float64Array":
            case "Int8Array":
            case "Int16Array":
            case "Int32Array":
            case "Uint8Array":
            case "Uint16Array":
            case "Uint32Array":
            case "Uint8ClampedArray":
            case "Arguments":
            case "Array":
                if (a.length != b.length) return false;
                for (element = 0; element < a.length; element++) {
                    if (!(element in a) && !(element in b)) continue; // empty slots are equal
                    // either one slot is empty but not both OR the elements are not equal
                    if (
                        element in a != element in b ||
                        !checkEquality(a[element], b[element], refs)
                    )
                        return false;
                }
                return true;
            case "Object":
                return checkEquality(getPrototypeOf(a), getPrototypeOf(b), refs);
            default:
                return false;
        }
    }

    return function (a, b) {
        return checkEquality(a, b, []);
    };
}

function Properties(global) {
    this.vars = {}
    this.updated = [];

    for (const key in global) {
        this.vars[key] = global[key]
    }

    this.set = function (varName, varValue) {
        this.vars[varName] = varValue;
        this.propsUpdated(varName);
    };

    this.propsUpdated = function (key) {
        if (this.updated.indexOf(key) === -1) {
            this.updated.push(key);
        }
    }

    this.get = function (varName) {
        return this.vars[varName];
    };

    this.isEmpty = function () {
        return Object.keys(this.vars).length === 0;
    };

    this.clear = function (varName) {
        delete this.vars[varName];
        this.propsUpdated(varName);
    };

    this.clearAll = function () {
        const _this = this;
        Object.keys(this.vars).forEach(function (key) {
            _this.propsUpdated(key)
        });
        this.vars = {};
    };
}

function Suite(vars) {
    this.stdout = [];
    this.tests = {};

    this.global = new Properties(vars);

    this.test = function (testName, func) {
        this.tests[testName] = func || null;
    };

    this.assert = function (condition, message) {
        if (!condition) {
            throw message || "Assert failed";
        }
    };

    this.isEqual = function (first, second, message) {
        if (!isEqual(first, second)) {
            throw message || "Assert failed";
        }
    };

    this.log = function (text) {
        this.stdout.push(text + "\n");
    };

    this.properties = this.global;
}

function ResponseHeaders(headers) {
    this.headers = headers;

    this.valueOf = function (headerName) {
        headerName = headerName.toLowerCase()
        for (const key in this.headers)
            if (key.toLowerCase() === headerName)
                return this.headers[key];
    }

    this.valuesOf = function (headerName) {
        headerName = headerName.toLowerCase();
        let values = []
        for (const key in this.headers)
            if (key.toLowerCase() === headerName)
                values.push(this.headers[key]);
        return values;
    };
}

function isEquivalent(a, b) {
    // Create arrays of property names
    var aProps = Object.getOwnPropertyNames(a);
    var bProps = Object.getOwnPropertyNames(b);

    // If number of properties is different,
    // objects are not equivalent
    if (aProps.length != bProps.length) {
        return false;
    }

    for (var i = 0; i < aProps.length; i++) {
        var propName = aProps[i];

        // If values of same property are not equal,
        // objects are not equivalent
        if (a[propName] !== b[propName]) {
            return false;
        }
    }

    // If we made it this far, objects
    // are considered equivalent
    return true;
}

var jsHandler = function (isJson, global, responseBody, statusCode, headers) {
    var client = new Suite(global);
    var response = {
        body: isJson ? JSON.parse(responseBody) : responseBody,
        status: statusCode,
        headers: new ResponseHeaders(headers),
    };

    // bind
    console.log = function (msg) {
        client.log(msg);
    }
    try {
        // don't edit this or modify this
        JS_CODE_REPLACE
        // don't edit this or modify this
    } catch (error) {
        client.log('error ' + error)
    }

    return client;
};