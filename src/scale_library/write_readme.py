"""
Write out README.

The scale-library README contains counts of scl files from each source. The
code in this file writes out a README with the counts populated. This allows
run_all.py to keep the scl counts in the README up to date.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def write_readme(
    *,
    total_scl_count,
    damusc_scl_count,
    divisions_scl_count,
    edos_scl_count,
    mailing_lists_scl_count,
    ord_cc32_scl_count,
    xenharmonikon_scl_count,
):
    readme_path = Path(__file__).parents[2] / "README.md"
    logger.info("Writing README to %s", readme_path.relative_to(Path.cwd()))
    readme_text = f"""# scale-library
A library of microtonal scales with sources attributed.

The library is available as a [browsable website](https://scalelibrary.org) with:

- Similar and approximate parent/child scales for each scale in the library
- Links to open scales directly in [Scale Workshop](https://scaleworkshop.plainsound.org)
- Links to recordings for some scales, including:
    - Recordings from the 1932 Cairo Congress of Arab Music
    - Recordings of specific gamelans
    - Videos and per-singer recordings of Georgian funeral music
    - Performances of scores from Xenharmonikon

See this [example scale page](https://scalelibrary.org/scales/cairo-congress/CD01_01_hijaz_Egypt/).

The `scales` directory contains the scl files for each scale. The scl files are
also available for download as a zip on the [releases
page](https://github.com/narenratan/scale-library/releases) and as a [Python
package](#python-package). The library currently contains {total_scl_count} scl files.

## Sources
The scales come from the following sources:

### Xenharmonikon: {xenharmonikon_scl_count} scl files
Xenharmonikon is an informal journal of experimental music. The
`scales/xenharmonikon` directory contains scl files for all the scales I could
find while reading the 18 printed issues of Xenharmonikon published 1974-2006
(Xenharmonikon is now an [online journal](https://www.xenharmonikon.org)). For example:
```
! xen12-wilson-07-eikosany.scl
!
1-3-7-9-11-15 Eikosany, Figure 7
 20
!
 45/44  ! 3*9*15
 35/33  ! 1*7*15
 12/11  ! 1*3*9
 7/6    ! 3*7*11
 105/88 ! 7*9*15
 5/4    ! 3*11*15
 14/11  ! 1*7*9
 4/3    ! 1*3*11
 15/11  ! 1*9*15
 35/24  ! 7*11*15
 3/2    ! 3*9*11
 14/9   ! 1*7*11
 35/22  ! 3*7*15
 5/3    ! 1*11*15
 56/33  ! 1*3*7
 7/4    ! 7*9*11
 20/11  ! 1*3*15
 15/8   ! 9*11*15
 21/11  ! 3*7*9
 2/1    ! 1*9*11
!
! Erv Wilson
! D'Alessandro, like a Hurricane
! Xenharmonikon 12 (1989)
!
! [info]
! source = Xenharmonikon
! whole_number = 12
```

### Mailing lists: {mailing_lists_scl_count} scl files
The `scales/mailing-lists` directory contains scl files extracted from the
[Yahoo tuning groups ultimate
backup](https://github.com/YahooTuningGroupsUltimateBackup/YahooTuningGroupsUltimateBackup),
an archive of several tuning related mailing lists. Each scl file includes a
URL for the message containing the scl file on the [Yahoo tuning groups
ultimate backup website](https://yahootuninggroupsultimatebackup.github.io),
which allows browsing the mailing lists in a readable form. For example:
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

### DaMuSc: {damusc_scl_count} scl files
[DaMuSc](https://github.com/jomimc/DaMuSc.git) is a database of musical scales.
It contains cent values for many theoretical and measured scales from around
the world, along with references to their source. The `scales/damusc` directory
contains scl files generated from the measured scales in the DaMuSc database,
each containing the reference to the scale's source. For example:
```
! Georgia_GVM206-M.scl
!
GVM206-M (Voice), Georgia
 7
!
 179.0
 358.0
 500.0
 701.0
 887.0
 1067.0
 1189.0
!
! Scherbaum, Frank; Mzhavanadze, Nana (2020). Svan Funeral Dirges (Zär):
! Musical Acoustical Analysis of a New Collection of Field Recordings.
! Musicologist, 4(2):138-167.
!
! [info]
! source = DaMuSc
! measured_id = M0311
! ref_id = 56
! country = Georgia
! doi = https://doi.org/10.33906/musicologist.782094
```

### ORD-CC32: {ord_cc32_scl_count} scl files
[ORD-CC32](https://zenodo.org/records/15682346) is the Open Research Dataset of
the 1932 Cairo Congress of Arab Music. It contains cent values computationally
extracted from the audio recordings available in the [Internet
Archive](https://archive.org/details/13.PsaumeDeLaTristesse). The
`scales/cairo-congress` directory contains the scl files for the scale tones
derived from each track.
```
! CD01_01_hijaz_Egypt.scl
!
Les nuits d'amour / Ô mon Commensal - Darwîsh Muhammad al-Harîrî (hijaz, Egypt)
 7
!
 134.661786
 390.582837
 502.627574
 717.672797
 851.945267
 1009.856558
 1200.0
!
! Bozkurt, B. (2025). An Open Research Dataset of the 1932 Cairo
! Congress of Arab Music. arXiv:2506.14503.
!
! [info]
! source = ORD-CC32
! doi = https://doi.org/10.5281/zenodo.15682346
! cd = 1
! track = 1
! mbid = d64461bb-c41b-4396-a671-caf846205b34
! maqam = hijaz
! region = Egypt
! tonic_ref = annotated
! tonic_hz = 135.23
```
Tracks where the tonic was annotated in the dataset (e.g.
`CD01_01_hijaz_Egypt.scl`) are marked `tonic_ref = annotated`; the remaining
tracks did not have the tonic annotated, so their scl files (e.g.
`CD02_03_Egypt.scl`) omit the maqam from the filename and use the lowest
detected peak as the tonic reference, so might not be the expected mode of the
maqam.

### Divisions of the Tetrachord: {divisions_scl_count} scl files
John Chalmers' book *Divisions of the Tetrachord*, available online
[here](https://eamusic.dartmouth.edu/~larry/published_articles/divisions_of_the_tetrachord/index.html),
contains a catalog of tetrachords in chapter 9. The
`scales/divisions-of-the-tetrachord` directory contains scl files for each of
the tetrachords in the catalog. For example:
```
! 475_D17.scl
!
Diatonic tetrachord 10/9 * 10/9 * 27/25, Al-Farabi
 3
!
 10/9
 100/81
 4/3
!
! Chalmers, John H. Divisions of the Tetrachord.
! Frog Peak Music, 1993.
!
! [info]
! source = Divisions of the Tetrachord
! catalog_index = 475
```

### EDOs: {edos_scl_count} scl files
The `scales/edos` directory contains scl files for equal divisions of the
octave from 1 through 72. For example:
```
! edo-09.scl
!
9 equal divisions of the octave
 9
!
 133.333333  ! 1\\9
 266.666667  ! 2\\9
 400.0       ! 3\\9
 533.333333  ! 4\\9
 666.666667  ! 5\\9
 800.0       ! 6\\9
 933.333333  ! 7\\9
 1066.666667 ! 8\\9
 1200.0      ! 9\\9
!
! Augusto Novaro, Sistema Natural de la Música, 1951.
!
! [info]
! source = EDO
```
On 9-EDO, Novaro wrote: "Los nueve sonidos proporcionan aproximaciones a los
intervalos 13/12, 34/27, 27/17 y 24/13; puede decirse que se obtienen perfectas
las relaciones 7/6 y 12/7." (The nine sounds provide approximations to the
intervals 13/12, 34/27, 27/17 and 24/13; one can say that the relations 7/6 and
12/7 are obtained perfectly.)


## Scale index
The scales come with an [index](scale-index.csv) giving each scale along with
details including number of notes, period, and prime limit (if just). For me
filtering this index in a spreadsheet (or [visidata](https://www.visidata.org)!)
is a very handy way of browsing the scales.

## An example
While setting up this library, I
[searched](https://github.com/surge-synthesizer/tuning-library-python/blob/main/examples/similar.py)
it for a scale similar to a version of Maqam Rast I use (with a second of 10/9
to make it easier to play on my guitar). I was very happy to find my scale was
within eleven cents of the DaMuSc scale `Georgia_GVM206-M.scl` given above. The
reference for the scale was to an [open access
paper](https://dergipark.org.tr/en/pub/musicologist/issue/58711/782094), which
introduced me to
[this](https://www.audiolabs-erlangen.de/resources/MIR/2017-GeorgianMusic-Scherbaum)
wonderful archive of videos and recordings from Georgia. In the archive I was
able to watch a
[video](https://www.audiolabs-erlangen.de/resources/MIR/2017-GeorgianMusic-Scherbaum/GVM206_ZariMestiaTake2_Zargash_MestiaSingers_20160814)
of the very performance from which the `Georgia_GVM206-M.scl` scale was
extracted. This is exactly the sort of thing I was hoping the references for
the scales would do - I hope it happens often!

And it turns out my scale is built from a tetrachord which is within three
cents of the tetrachord due to Al-Farabi in `475_D17.scl` above. Divisions of
the Tetrachord gives examples in the same genus from Ptolemy and Avicenna.

Also my scale is within three cents of the seventh mode of the scale in
`synpor4.scl` from the tuning-math mailing list. The linked email gives related
scales which are all Fokker blocks according to the subject.

## Other scale libraries

These great scale libraries may also be of interest:

- The tunings in [Leimma](https://isartum.net/leimma). These all come with sources attributed.
- Sevish's [tuning files](https://sevish.com/music-resources/#tuning-files) give sources in the accompanying PDFs
- The [Scala scale archive](https://www.huygens-fokker.org/microtonality/scales.html)
- Wilson's garden, a scale collection built into [Wilsonic](https://github.com/marcus-w-hobbs/Wilsonic-MTS-ESP)
- The [tuning library](https://github.com/surge-synthesizer/surge/tree/main/resources/data/tuning_library) included with Surge XT
- The tunings which come with [Semantic Daniélou-53](https://www.semantic-danielou.com/semantic-danielou-53/download-and-installation-semantic-danielou-53/)
- Ableton comes with a library of [tunings](https://tuning.ableton.com)

In case it isn't clear, `scale-library` is independent of the Scala scale archive.

## Python package

`scale-library` is available as a Python [package](https://pypi.org/project/scale-library/):

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

Parse a `scale-library` scl file `[info]` block containing structured metadata:

```python
>>> import scale_library as sl
>>> from pprint import pprint
>>>
>>> scl_text = (sl.scale_dir() / "mailing-lists/xenoga24.scl").read_text()
>>> info = sl.parse_scl_info(scl_text)
>>>
>>> pprint(info)
{{'file': 'tuning/messages/yahoo_tuning_messages_api_raw_0-19436.json',
 'msg_id': '16640',
 'source': 'Mailing lists',
 'topic_id': '16640'}}
```
"""
    readme_path.write_text(readme_text)
