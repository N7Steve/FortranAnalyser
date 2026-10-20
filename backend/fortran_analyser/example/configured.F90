! La configuración de compilación debe decidir qué rama utilizar.
! Esta fuente se muestra como parcial, sin métricas inventadas.
#ifdef DOUBLE_PRECISION
module precision
  implicit none
  integer, parameter :: rk = selected_real_kind(15)
end module
#else
module precision
  implicit none
  integer, parameter :: rk = kind(1.0)
end module
#endif
