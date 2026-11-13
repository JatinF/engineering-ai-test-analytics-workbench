# applied = false
# terraform was not executed. kubectl was not executed.
# This sketch documents an AWS EKS-shaped placement for a later environment.
# It is not a production deployment and it was not applied.

variable "applied" {
  type    = bool
  default = false
}

# aws_eks_cluster.workbench would live in a private subnet.
# The API container would listen on 8000 behind an internal load balancer.
# Synthetic lab data would stay in a private database. No factory network is attached.

output "applied" {
  value = var.applied
}
