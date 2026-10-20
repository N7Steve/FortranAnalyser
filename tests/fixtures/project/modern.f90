! Synthetic validation fixture; GPL-3.0-or-later, see LICENSE.txt.
module modern
  implicit none ! inline comment must not disable detection
contains
  subroutine update(n, values)
    integer, intent(in) :: n
    real, intent(inout) :: values(n)
    integer :: i, j, &
               shadow, scratch
    character(len=20) :: text
    text = 'DO ! CALL INCLUDE'
    do i = 1, n
      do j = 1, n
        values(i) = values(i) + real(j)
      end do
    end do
    shadow = 1
    scratch = shadow
    call consume(scratch)
  end

  real function twice(x)
    real, intent(in) :: x
    real :: a, b, c, d
    a = x
    b = a
    c = b
    d = c
    twice = 2 * d
  end function
end module
