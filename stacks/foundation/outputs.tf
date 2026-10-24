output "policy_contract" {
  description = "Configuration from real module resources; test values are synthetic, never cloud evidence."
  value = {
    network         = module.network.policy_contract
    private_compute = module.private_compute.policy_contract
  }
}

output "resource_count" {
  description = "Number of configured resources; zero by default."
  value       = module.network.policy_contract.resource_count + module.private_compute.policy_contract.resource_count
}
