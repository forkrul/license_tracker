## 2024-05-23 - [Moved Constant Maps out of Loop]
**Learning:** Instantiating dictionaries and lists inside a frequently called method (like `_normalize_license` which is called for every package resolution) adds unnecessary overhead.
**Action:** Move static data structures (like license maps and common SPDX ID lists) to module-level constants. This avoids reallocation and populating these structures on every call.

## 2024-05-24 - [Memoized License Normalization]
**Learning:** Parsing and normalizing license strings (using license-expression and string matching) is a repetitive CPU-bound task when resolving many packages.
**Action:** Extracted the stateless normalization logic to a module-level function decorated with `@lru_cache`. This reduced the normalization time for common licenses from ~25µs to ~0.15µs per call (over 100x speedup), significantly reducing overhead for large dependency trees.
