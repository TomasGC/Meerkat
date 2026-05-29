package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "mycli",
	Short: "A sample CLI application",
}

var deployCmd = &cobra.Command{
	Use:   "deploy",
	Short: "Deploy application",
	Run: func(cmd *cobra.Command, args []string) {
		force, _ := cmd.Flags().GetBool("force")
		env, _ := cmd.Flags().GetString("environment")
		fmt.Printf("Deploying to %s (force: %v)\n", env, force)
	},
}

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Manage configuration",
}

var setConfigCmd = &cobra.Command{
	Use:   "set",
	Short: "Set configuration value",
	Run: func(cmd *cobra.Command, args []string) {
		key, _ := cmd.Flags().GetString("key")
		value, _ := cmd.Flags().GetString("value")
		fmt.Printf("Setting %s = %s\n", key, value)
	},
}

func init() {
	deployCmd.Flags().BoolP("force", "f", false, "Force deployment")
	deployCmd.Flags().StringP("environment", "e", "production", "Target environment")

	setConfigCmd.Flags().StringP("key", "k", "", "Configuration key")
	setConfigCmd.Flags().StringP("value", "v", "", "Configuration value")

	configCmd.AddCommand(setConfigCmd)
	rootCmd.AddCommand(deployCmd)
	rootCmd.AddCommand(configCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
