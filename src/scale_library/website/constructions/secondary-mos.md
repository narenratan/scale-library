# Secondary moments of symmetry

A secondary moment of symmetry (MOS) is built from a larger parent MOS by
stepping through it in steps of a given size, wrapping at the period. For
example, take the parent MOS as the seven-note scale built by stacking
4/3

<pre class="narrow">
1/1, 9/8, 81/64, 4/3, 3/2, 27/16, 243/128
</pre>

Stepping through five times in steps of three scale degrees, we can choose to
start on each of the seven scale degrees, giving the seven sets of notes

<pre class="narrow">
1:  1/1,     4/3,     243/128, 81/64,   27/16
2:  9/8,     3/2,     1/1,     4/3,     243/128
3:  81/64,   27/16,   9/8,     3/2,     1/1
4:  4/3,     243/128, 81/64,   27/16,   9/8
5:  3/2,     1/1,     4/3,     243/128, 81/64
6:  27/16,   9/8,     3/2,     1/1,     4/3
7:  243/128, 81/64,   27/16,   9/8,     3/2
</pre>

Sorting and taking the lowest note in each scale as tonic gives

<pre class="narrow">
1:  1/1,     81/64,   4/3,     27/16,   243/128
2:  1/1,     9/8,     4/3,     3/2,     243/128
3:  1/1,     9/8,     81/64,   3/2,     27/16
4:  1/1,     9/8,     32/27,   3/2,     27/16
5:  1/1,     81/64,   4/3,     3/2,     243/128
6:  1/1,     9/8,     4/3,     3/2,     27/16
7:  1/1,     9/8,     4/3,     3/2,     27/16
</pre>

This is a family of secondary MOS called the Tanabe cycle.

Only five of the seven scales are unique (not modes of each other).

The ordinary five-note MOS from stacking 4/3 has two step sizes

<pre class="narrow">
S = 9/8
T = 32/27
</pre>

The family of secondary MOS together use four step sizes
<pre class="narrow">
S1 = 9/8
S2 = 256/243
T1 = 32/27
T2 = 81/64
</pre>

In general, starting with an N-note parent MOS, which has two step sizes, we get
a family of n distinct n-note secondary MOS (where n < N), together using four
step sizes.

## Further reading

- [Introduction to Erv Wilson's Moments of Symmetry](https://www.anaphoria.com/wilsonintroMOS.html), The Wilson Archives
