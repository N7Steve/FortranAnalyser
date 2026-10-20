C     Ejemplo sintetico de codigo antiguo. GPL-3.0-or-later.
      SUBROUTINE NORMALIZE(N,X)
      INTEGER N,I
      REAL X(N),TOTAL
      TOTAL=0.0
      DO 100 I=1,N
      TOTAL=TOTAL+X(I)
  100 CONTINUE
      IF (TOTAL.GT.0.0) THEN
        DO 200 I=1,N
        X(I)=X(I)/TOTAL
  200   CONTINUE
      ENDIF
      END
