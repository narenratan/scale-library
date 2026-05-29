# Recurrent sequence scales

Given a recurrent sequence like the Fibonacci sequence

<pre class="narrow">
1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, ...
</pre>

pick a start point and end point, say 3 and 34, take the segment between them

<pre class="narrow">
3, 5, 8, 13, 21, 34
</pre>

divide by the smallest term

<pre class="narrow">
3/3, 5/3, 8/3, 13/3, 21/3, 34/3
</pre>

then octave-reduce and sort to give the scale

<pre class="narrow">
1/1, 13/12, 4/3, 17/12, 5/3, 7/4
</pre>

with period 2/1.

As you move along a recurrent sequence, the ratio between successive terms
approaches a limit (1.618, or 833¢, for the Fibonacci sequence). This means
that segments far along the sequence approach scales built by stacking a
generator. This gives a connection to [moments of
symmetry](/constructions/mos).

## Further reading

- Warren Burt, [Developing and Composing With Scales based on Recurrent
  Sequences](http://www.warrenburt.com/storage/selected_articles/Burt2002bRecurrentSequencesACMC02.pdf)
- [An introduction to the scales of Mt Meru and other recurrent sequence
  scales](https://www.anaphoria.com/wilsonintroMERU.html), The Wilson Archives
