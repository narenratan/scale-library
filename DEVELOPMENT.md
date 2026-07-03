# Commands that I always forget

Build the library itself:

> uv run python src/scale_library/run_all.py

Build the website:

> uv run python -m scale_library.website

Run a local http server to look at the website:

> python3 -m http.server 8000 --bind 127.0.0.1 --directory site

Build the data Python package:

> cd data-package
> uv build --wheel

Upload the Python package to test PyPI:

> uvx twine upload --repository testpypi dist/*.whl

and to real PyPI:

> uvx twine upload dist/*.whl
