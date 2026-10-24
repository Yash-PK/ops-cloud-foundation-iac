output "policy_contract" {
  description = "Configuration from real state-bootstrap resources, exposed for mocked plan assertions."
  value       = module.state_bootstrap.policy_contract
}

output "resource_count" {
  description = "Number of configured resources; zero by default."
  value       = module.state_bootstrap.policy_contract.resource_count
}

output "backend_configuration" {
  description = "Future coordinates only; the active backend is local and migration remains unauthorized."
  value       = module.state_bootstrap.backend_configuration
}
