// Filename: src/pages/LoginPage.jsx
import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Button } from '@/components/ui/button'; // Assuming shadcn/ui
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'; // Corrected import
import { toast } from 'sonner';
import { FiLogIn, FiEye, FiEyeOff } from 'react-icons/fi';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard"; // Redirect to intended page or dashboard

  const usernameInputRef = React.useRef(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    const result = await auth.login(username, password);

    if (result.success) {
      toast.success("Login successful! Redirecting...");
      navigate(from, { replace: true });
    } else {
      // Error toast is already shown by the auth context
      setError(result.error);
      setIsLoading(false);
      usernameInputRef.current?.focus(); // Focus username input on error
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-green-400 via-teal-500 to-blue-600 dark:from-gray-800 dark:via-gray-900 dark:to-black p-4">
      <Card className="w-full max-w-md shadow-2xl dark:bg-gray-800">
        <CardHeader className="text-center">
          <div className="inline-block p-3 bg-green-500 dark:bg-green-600 rounded-full mx-auto mb-4">
            <FiLogIn className="h-8 w-8 text-white" />
          </div>
          <CardTitle className="text-3xl font-bold text-gray-800 dark:text-gray-100">Welcome Back!</CardTitle>
          <CardDescription className="text-gray-600 dark:text-gray-400">
            Log in to your WhatsApp CRM dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {error && <p className="text-sm text-red-500 dark:text-red-400 bg-red-100 dark:bg-red-900/30 p-3 rounded-md text-center">{error}</p>}
            <div className="space-y-2">
              <Label htmlFor="username" className="text-gray-700 dark:text-gray-300">Username</Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter your username"
                required
                ref={usernameInputRef}
                disabled={isLoading}
                className="dark:bg-gray-700 dark:border-gray-600 dark:text-gray-50"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password"className="text-gray-700 dark:text-gray-300">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  disabled={isLoading}
                  className="dark:bg-gray-700 dark:border-gray-600 dark:text-gray-50 pr-10"
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200" aria-label={showPassword ? "Hide password" : "Show password"}>
                  {showPassword ? <FiEyeOff /> : <FiEye />}
                </button>
              </div>
            </div>
            <Button type="submit" className="w-full bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 text-white" disabled={isLoading}>
              {isLoading ? 'Logging in...' : 'Log In'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col items-center text-xs text-gray-500 dark:text-gray-400 pt-4">
          <p>&copy; {new Date().getFullYear()} AutoWhatsapp CRM</p>
          {/* <Link to="/forgot-password" className="hover:text-green-600 dark:hover:text-green-400">Forgot password?</Link> */}
        </CardFooter>
      </Card>
    </div>
  );
}
