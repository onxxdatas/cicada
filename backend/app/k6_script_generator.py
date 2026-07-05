"""
Turns a Test row's configuration into a runnable k6 script.
k6 scripts are plain JavaScript, so this is string templating rather than
AST generation — but everything user-supplied is passed through
JSON.stringify-equivalent encoding (json.dumps) so it can't break out of the
generated script.
"""




import json
from app.models import Test





def generate_k6_script(test: Test) -> str:
    headers = json.dumps(test.headers or {})
    if test.method.upper() in {"GET", "HEAD"}:
      body = "null"
    else:
      body = json.dumps(test.body) if test.body is not None else "null"
    method = json.dumps(test.method.upper())
    url = json.dumps(test.target_url)

    if test.stages:
        stages_js = json.dumps([{"duration": s["duration"], "target": s["target"]} for s in test.stages])
        vus_option = ""
        stages_option = f"stages: {stages_js},"
    else:
        # No stages defined: flat load at `vus` for a default 25s.
        vus_option = f"vus: {test.vus},\n  duration: '25s',"
        stages_option = ""

    thresholds_js = "{}"
    if test.thresholds:
        thresholds_map = {}
        for t in test.thresholds:
            thresholds_map.setdefault(t["metric"], []).append(t["expression"])
        thresholds_js = json.dumps(thresholds_map)

    return f"""\
import http from 'k6/http';
import {{ check, sleep }} from 'k6';

export const options = {{
  {vus_option}
  {stages_option}
  thresholds: {thresholds_js},
}};

const HEADERS = {headers};
const METHOD = {method};
const URL = {url};
const BODY = {body};

export default function () {{
  const params = {{ headers: HEADERS }};
  let res;

  if (METHOD === 'GET' || METHOD === 'HEAD') {{
    res = http.request(METHOD, URL, null, params);
  }} else {{
    res = http.request(METHOD, URL, BODY, params);
  }}

  check(res, {{
    'status is < 400': (r) => r.status < 400,
  }});

  sleep(1);
}}
"""
