# scale-library

Python package bundling the data from
[scale-library](https://scalelibrary.org), a library of microtonal scales with
sources attributed.

- `scale_dir()` returns the path to the directory containing the bundled scl files
- `scale_index_path()` returns the path to the scale index csv
- `parse_scl_info(text)` parses the `scale-library` scl file `[info]` blocks containing structured metadata

Install `scale-library`:

```bash
$ pip install scale-library
```

Read an individual scl file:

```python
>>> import scale_library as sl
>>>
>>> scl_path = sl.scale_dir() / "damusc/Georgia_GVM206-M.scl"
>>> scl_text = scl_path.read_text()
```

Read the scale index as a dataframe:

```python
>>> import pandas as pd
>>> import scale_library as sl
>>>
>>> scale_index_df = pd.read_csv(sl.scale_index_path())
```

The scl files in `scale-library` contain `[info]` blocks for structured metadata, for example:

```
! xenoga24.scl
!
Xeno-Gothic rational adaptive tuning, 3-7 ratios (keyboards 64:63 apart) 
24
!
 64/63
 2187/2048
 243/224
 9/8 
 8/7
 32/27
 2048/1701
 81/64
 9/7
 4/3 
 256/189
 729/512
 81/56
 3/2
 32/21
 6561/4096
 729/448
 27/16
 12/7
 16/9
 1024/567
 243/128
 27/14
 2/1
!
! https://yahootuninggroupsultimatebackup.github.io/tuning/topicId_16640.html#16640
!
! [info]
! source = Mailing lists
! file = tuning/messages/yahoo_tuning_messages_api_raw_0-19436.json
! topic_id = 16640
! msg_id = 16640
```

Parse a `scale-library` scl file `[info]` block:

```python
>>> import scale_library as sl
>>> from pprint import pprint
>>>
>>> scl_text = (sl.scale_dir() / "mailing-lists/xenoga24.scl").read_text()
>>> info = sl.parse_scl_info(scl_text)
>>>
>>> pprint(info)
{'file': 'tuning/messages/yahoo_tuning_messages_api_raw_0-19436.json',
 'msg_id': '16640',
 'source': 'Mailing lists',
 'topic_id': '16640'}
```
