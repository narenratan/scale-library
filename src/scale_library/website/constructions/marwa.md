# Marwa permutations

Any seven-note scale can be built by stacking 'variable-sized fourths' found by
stepping through the scale taking every third note (in a seven-note scale a
fourth spans three scale steps). For example, taking the scale

<pre class="narrow">
1/1, 9/8, 7/6, 4/3, 3/2, 14/9, 7/4, 2/1
</pre>

stepping through by three steps, wrapping at the octave

<pre class="narrow">
4/3  /  1/1   ->  4/3
7/4  /  4/3   ->  21/16
7/6  /  7/4   ->  4/3
14/9 /  7/6   ->  4/3
9/8  /  14/9  ->  81/56
3/2  /  9/8   ->  4/3
2/1  /  3/2   ->  4/3
</pre>

we get the fourths


<pre class="narrow">
4/3, 21/16, 4/3, 4/3, 81/56, 4/3, 4/3
</pre>

Stacking these fourths gives

<pre class="narrow">
                  1/1
1/1  *  4/3   ->  4/3
4/3  *  21/16 ->  7/4
7/4  *  4/3   ->  7/6
7/6  *  4/3   ->  14/9
14/9 *  81/56 ->  9/8
9/8  *  4/3   ->  3/2
3/2  *  4/3   ->  2/1
</pre>

reproducing our original scale.

By stacking the same fourths in a different order, we get scales related to our
original scale; these are called Marwa permutations. For example, permuting the
fourths to give

<pre class="narrow">
4/3, 21/16, 4/3, 81/56, 4/3, 4/3, 4/3
</pre>

and stacking gives the scale

<pre class="narrow">
1/1, 9/8, 7/6, 4/3, 3/2, 27/16, 7/4, 2/1
</pre>

different from the original scale or any of its modes.

As starting scales, Wilson takes tetrachordal scales built from two of the same
tetrachord. For example, stacking the steps of Archytas' diatonic tetrachord (28/27,
8/7, 9/8), a whole tone 9/8, and those steps again gives the scale

<pre class="narrow">
1/1, 28/27, 32/27, 4/3, 3/2, 14/9, 16/9, 2/1
</pre>

which is built from fourths

<pre class="narrow">
4/3, 4/3, 4/3, 21/16, 4/3, 81/56, 4/3
</pre>

Our example scale fourths are a permutation of these.

Wilson has a specific scheme for which permutations to consider, perhaps best
appreciated by looking at the diagrams in the Marwa Permutations paper and
implemented in the code below.

## Further reading

- Erv Wilson, [The Marwa Permutations](https://www.anaphoria.com/xen9mar.pdf),
  Xenharmonikon 9 (1986)
- John Chalmers, [Divisions of the Tetrachord](https://eamusic.dartmouth.edu/~larry/published_articles/divisions_of_the_tetrachord/index.html),
  Frog Peak Music (1993), Chapter 6, p. 110
