| Accepted File Types| Assumed Reference Frame| Assumed Euler Angle Units| Default Rotations Applied|Criteria for Flagging GOOD Data| Criteria for Cleanup of BAD Data| Notes|
|---|---|---|---|---|---|---|
| CTF| HKL| Degrees| 0 deg about <001>| ERROR < 1| BC < 50\*| \* Band Contrast (BC) value of 50 is determined by taking 20% of allowable range [0,255]. If BC cleanup threshold is set to 0, then no additional cleanup will be applied.|
| ANG| TSL| Radians| 90 deg about <001>| CI > 0.05| CI < 0.20 \*| \* Confidence Index (CI) value of 0.20 is determined by taking 20% of allowable range [0,1]. If CI cleanup threshold is less than or equal to the value used to flag GOOD data (default 0.05), no additional cleanup will be applied.|


| Filter Name| Description| Threshold Value(s) - CTF| Threshold Values(s) - ANG|
|---|---|---|---|
| Threshold Objects| Calculates mask of good data (inverse is used to find bad data)| Error < 1| CI > 0.05, IQ > 20,000|
| Neighbor Orientation Comparison (Bad Data)| Changes bad pixels to good (mask) if specified number of neighbors are within user-defined misorientation threshold| Misorientation Tolerance: 5 deg<br>Required Number of Neighbors: 3| Misorientation Tolerance: 5 deg<br>Required Number of Neighbors: 3|
| Replace Element Attributes with Neighbor (Threshold)| (primary cleanup) Data for pixels below a user-defined quality threshold are replaced with data of most confident neighbor. Changes mask, but does not depend on it| BC < 30| CI < 0.05|
| Neighbor Orientation Correlation| (secondary cleanup) Data for pixels below a user-defined quality threshold are conditionally replaced with data of neighbors. Changes mask, but does not depend on it| BC < 50| CI < 0.10|
| Erode / Dilate Bad Data| Erodes bad data (using mask)| 2 iterations| 2 iterations|
| Erode / Dilate Bad Data| Dilates bad data (using mask)| 2 iterations| 2 iterations|
| Fill Bad Data| Fills bad data below certain size| Minimum defect size = 1000 um2| Minimum defect size = 1000 um2|