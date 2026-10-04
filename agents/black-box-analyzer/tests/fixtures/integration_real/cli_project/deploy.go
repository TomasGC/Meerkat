package main

import "github.com/spf13/cobra"

var (
	force       bool
	environment string
)

var deployCmd = &cobra.Command{
	Use:   "deploy",
	Short: "Deploy the application to an environment",
	RunE:  runDeploy,
}

var configSetCmd = &cobra.Command{
	Use:   "set",
	Short: "Set a configuration value",
	RunE:  runConfigSet,
}

func init() {
	deployCmd.Flags().BoolVarP(&force, "force", "f", false, "deploy without confirmation")
	deployCmd.Flags().StringVarP(&environment, "environment", "e", "dev", "target environment")
	rootCmd.AddCommand(deployCmd)
	rootCmd.AddCommand(configSetCmd)
}

func runDeploy(cmd *cobra.Command, args []string) error {
	return nil
}

func runConfigSet(cmd *cobra.Command, args []string) error {
	return nil
}
