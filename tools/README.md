qbplotter
=========

```
⇒  python qbplotter.py --src ./samples/spotA.qb --x 502 --y 502
Loading ./samples/spotA.qb
Loading Matrix b'' with size (18, 9, 16)
Object contains 384 voxels
Plot start position (502, 502, 0)
Owner 4
Connecting with XXX
0/384 voxels
100/384 voxels
200/384 voxels
300/384 voxels
```


Options
-------
- -src           .qb file full path             string
- --owner         to plot as player 0..X         int
- --x --y --z     plot offset in the World       int
- --sleep         delay in ms between plots      int
- --turg-url      theurbn backend url            string

Fixtures
--------
- samples/spotA.qb
<p align="center">
	<img src="https://github.com/TheURBN/turg/raw/master/tools/samples/spotA.png" alt="allexx was here"/>
</p>
- sample/spotB.qb
<p align="center">
	<img src="https://github.com/TheURBN/turg/raw/master/tools/samples/spotB.png" alt="allexx was here"/>
</p>