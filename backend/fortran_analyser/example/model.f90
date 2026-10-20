! Proyecto sintético de demostración. GPL-3.0-or-later.
module transport_model
  implicit none
contains
  subroutine advance(n, concentration)
    integer, intent(in) :: n
    real, intent(inout) :: concentration(n)
    integer :: i, j, k, step
    ! Cuatro bucles: una observación de legibilidad, no de rendimiento.
    do step = 1, 2
      do i = 1, n
        do j = 1, n
          do k = 1, n
            concentration(i) = concentration(i) + 0.01
          end do
        end do
      end do
    end do
  end subroutine

  real function total_mass(values)
    real, intent(in) :: values(:)
    total_mass = sum(values)
  end function
end module
