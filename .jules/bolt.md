## 2024-05-23 - [Moved Constant Maps out of Loop]
**Learning:** Instantiating dictionaries and lists inside a frequently called method (like `_normalize_license` which is called for every package resolution) adds unnecessary overhead.
**Action:** Move static data structures (like license maps and common SPDX ID lists) to module-level constants. This avoids reallocation and populating these structures on every call.
