// Admin access hook
export const useAdminAccess = () => {
  return {
    hasAccess: true,
    permissions: ['system_admin']
  }
}

export default useAdminAccess