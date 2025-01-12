# Scale library
A library of microtonal scales with sources attributed.

The `scales` directory contains the scl files for each scale. The scl files are
also available for download as a zip on the [releases
page](https://github.com/narenratan/scale-library/releases). The library
currently contains 2478 scl files.

## Sources
The scl files are generated from the following sources:

### Mailing lists: 1329 scl files
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

### DaMuSc: 426 scl files
[DaMuSc](https://github.com/jomimc/DaMuSc.git) is a database of musical scales.
It contains cent values for many theoretical and measured scales from around
the world, along with references to their source. The
`scales/database-of-musical-scales` directory contains scl files generated from
the measured scales in the DaMuSc database, each containing the reference to
the scale's source. For example:
```
! Georgia_GVM206-M.scl
!
Measured scale M0311 in DaMuSc
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
! N. Mzhavanadze and F. Scherbaum. Svan funeral dirges (zar): Musical
! acoustical analysis of a new collection of field recordings.
! Musicologist, 4(2):138-167, 2020. doi: 10.33906/musicologist.782094
!
! [info]
! source = DaMuSc
! measured_id = M0311
! ref_id = 56
```

### Divisions of the Tetrachord: 723 scl files
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

## An example
While setting up this library, I
[searched](https://github.com/surge-synthesizer/tuning-library-python/blob/main/examples/similar.py)
it for a scale similar to a version of Maqam Rast I use (with a second of 10/9
to make it easier to play on my guitar). I was very happy to find my scale was
within four cents of the DaMuSc scale `Georgia_GVM206-M.scl` given above. The
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
- The [Scala scale archive](https://www.huygens-fokker.org/microtonality/scales.html)
- Wilson's garden, a scale collection built into [Wilsonic](https://github.com/marcus-w-hobbs/Wilsonic-MTS-ESP)
- The [tuning library](https://github.com/surge-synthesizer/surge/tree/main/resources/data/tuning_library) included with Surge XT
- Ableton comes with a library of [tunings](https://tuning.ableton.com)
