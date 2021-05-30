function Properties(global) {
    this.vars = {}

    for (var key in global) {
        this.vars[key] = global[key]
    }

    this.set = function (varName, varValue) {
        this.vars[varName] = varValue;
    };

    this.get = function (varName) {
        return this.vars[varName];
    };

    this.isEmpty = function () {
        return Object.keys(this.vars).length == 0;
    };

    this.clear = function (varName) {
        delete this.vars[varName];
    };

    this.clearAll = function () {
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

var jsHandler = function (isJson, global, responseBody, statusCode, headers) {
    var client = new Suite(global);
    var response = {
        body: isJson ? JSON.parse(responseBody) : responseBody,
        status: statusCode,
        headers: new ResponseHeaders(headers),
        "hai": statusCode
    };

    // don't edit this or modify this
    JS_CODE_REPLACE
    // don't edit this or modify this
    return client;
};