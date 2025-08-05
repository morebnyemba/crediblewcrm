// Filename: src/components/DashboardLayout.jsx
import React, { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Button } from './ui/button';
import { Skeleton } from './ui/skeleton';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from './ui/tooltip';
import { useMediaQuery } from 'react-responsive';

import {
  FiSettings,
  FiMessageSquare,
  FiDatabase,
  FiMenu,
  FiHome,
  FiLink,
  FiClock,
  FiX,
  FiChevronLeft,
  FiChevronRight,
  FiShare2,
  FiUsers,
  FiImage,
  FiUser
} from 'react-icons/fi';

const links = [
  { to: '/dashboard', label: 'Dashboard', icon: <FiHome className="h-5 w-5" /> },
  { to: '/conversation', label: 'Conversations', icon: <FiMessageSquare className="h-5 w-5" />, badge: 5 },
  { to: '/contacts', label: 'Contacts', icon: <FiUsers className="h-5 w-5" /> },
  { to: '/flows', label: 'Flows', icon: <FiShare2 className="h-5 w-5" /> },
  { to: '/media-library', label: 'Media Library', icon: <FiImage className="h-5 w-5" />, badge: 12 },
  { to: '/api-settings', label: 'API Settings', icon: <FiSettings className="h-5 w-5" /> },
];

const DashboardBackground = () => (
  <div className="absolute inset-0 bg-white dark:bg-gray-950 overflow-hidden -z-10">
    <div
      className="absolute inset-0 opacity-[0.06] dark:opacity-[0.04]"
      style={{
        backgroundImage: `repeating-linear-gradient(45deg, #a855f7 0, #a855f7 1px, transparent 0, transparent 50%)`,
        backgroundSize: '12px 12px',
      }}
    />
    <div className="absolute inset-0 bg-gradient-to-br from-white via-white/0 to-white dark:from-gray-950 dark:via-gray-950/0 dark:to-gray-950" />
  </div>
);

export default function DashboardLayout() {
  const isMobile = useMediaQuery({ maxWidth: 767 });
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const savedState = localStorage.getItem('sidebarCollapsed');
      return savedState ? savedState === 'true' : isMobile;
    }
    return isMobile;
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    if (isMobile) {
      setCollapsed(true);
    } else {
      setCollapsed(localStorage.getItem('sidebarCollapsed') === 'true');
    }
  }, [isMobile]);

  useEffect(() => {
    if (!isMobile) {
      setMobileMenuOpen(false);
    }
  }, [isMobile]);

  useEffect(() => {
    if (!isMobile) {
      localStorage.setItem('sidebarCollapsed', collapsed);
    }
  }, [collapsed, isMobile]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [mobileMenuOpen]);

  return (
    <div className="flex min-h-screen bg-gray-100 dark:bg-slate-900 text-gray-800 dark:text-gray-200">
      {/* Mobile Header */}
      <header className="md:hidden fixed top-0 left-0 right-0 h-16 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 p-4 flex items-center justify-between z-50 shadow-sm">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700"
            aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
          >
            {mobileMenuOpen ? <FiX className="h-6 w-6" /> : <FiMenu className="h-6 w-6" />}
          </Button>
          <Link to="/dashboard" className="flex items-center">
            <span className="font-bold text-xl bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 dark:from-purple-400 dark:via-pink-400 dark:to-red-400 bg-clip-text text-transparent">
              AutoWhatsapp
            </span>
          </Link>
        </div>
        <Button variant="ghost" size="icon" className="rounded-full h-9 w-9">
          <FiUser className="h-5 w-5" />
        </Button>
      </header>

      {/* Mobile Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm md:hidden z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar - Full height */}
      <aside
        className={`fixed top-0 left-0 bottom-0 z-50 md:relative h-screen transition-all duration-300 ease-in-out border-r border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 ${
          collapsed ? 'md:w-20' : 'md:w-64'
        } ${
          mobileMenuOpen
            ? 'translate-x-0 w-full shadow-xl'
            : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="h-full flex flex-col">
          {/* Header */}
          <div className={`flex items-center p-4 border-b border-gray-200 dark:border-slate-700 ${
            collapsed ? 'justify-center' : 'justify-between'
          }`}>
            <Link 
              to="/dashboard" 
              className={`flex items-center gap-2 ${collapsed ? 'w-auto' : 'w-full'}`}
              onClick={() => isMobile && setMobileMenuOpen(false)}
            >
              <img 
                src="https://placehold.co/36x36/A855F7/FFFFFF?text=AW&font=roboto" 
                alt="AW Logo" 
                className="h-9 w-9 rounded-lg"
              />
              {!collapsed && (
                <span className="font-bold bg-gradient-to-r from-purple-600 via-pink-500 to-red-500 dark:from-purple-400 dark:via-pink-400 dark:to-red-400 bg-clip-text text-transparent text-xl">
                  AutoWhatsapp
                </span>
              )}
            </Link>
            {!isMobile && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCollapsed(!collapsed)}
                className="rounded-md text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-slate-700"
                aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {collapsed ? <FiChevronRight className="h-5 w-5" /> : <FiChevronLeft className="h-5 w-5" />}
              </Button>
            )}
          </div>

          {/* Navigation - Takes remaining space */}
          <nav className="flex-1 overflow-y-auto p-2">
            <TooltipProvider delayDuration={100}>
              {links.map((link) => {
                const isActive = link.to === '/dashboard' 
                  ? location.pathname === link.to 
                  : location.pathname.startsWith(link.to);
                
                return (
                  <Tooltip key={link.to}>
                    <TooltipTrigger asChild>
                      <Button
                        variant={isActive ? 'secondary' : 'ghost'}
                        className={`w-full justify-start text-sm font-medium h-10 group rounded-lg mb-1 ${
                          collapsed ? 'px-0 justify-center' : 'px-3 gap-3'
                        } ${
                          isActive
                            ? 'bg-purple-100 dark:bg-purple-500/20 text-purple-700 dark:text-purple-300'
                            : 'text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-700/80'
                        }`}
                        asChild
                      >
                        <Link
                          to={link.to}
                          onClick={() => isMobile && setMobileMenuOpen(false)}
                        >
                          <span className={`flex-shrink-0 h-5 w-5 ${
                            isActive 
                              ? 'text-purple-600 dark:text-purple-300' 
                              : 'text-gray-500 dark:text-gray-400 group-hover:text-gray-700 dark:group-hover:text-gray-200'
                          }`}>
                            {link.icon}
                          </span>
                          {!collapsed && (
                            <span className="truncate flex-1 text-left">
                              {link.label}
                              {link.badge && (
                                <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 text-xs font-medium rounded-full bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300">
                                  {link.badge}
                                </span>
                              )}
                            </span>
                          )}
                          {collapsed && link.badge && (
                            <span className="absolute top-0 right-0 -mt-1 -mr-1 flex h-4 w-4 items-center justify-center rounded-full bg-purple-500 text-xs text-white">
                              {link.badge > 9 ? '9+' : link.badge}
                            </span>
                          )}
                        </Link>
                      </Button>
                    </TooltipTrigger>
                    {collapsed && (
                      <TooltipContent 
                        side="right" 
                        className="bg-gray-800 dark:bg-slate-900 text-white text-xs rounded-md px-2 py-1 shadow-lg border border-transparent dark:border-slate-700"
                      >
                        {link.label}
                        {link.badge && ` (${link.badge})`}
                      </TooltipContent>
                    )}
                  </Tooltip>
                );
              })}
            </TooltipProvider>
          </nav>

          {/* Footer - Sticks to bottom */}
          <div className="border-t border-gray-200 dark:border-slate-700">
            <div className={`flex items-center gap-3 p-4 hover:bg-gray-100 dark:hover:bg-slate-700 ${
              collapsed ? 'justify-center' : 'px-3'
            }`}>
              <div className="relative">
                <img 
                  src="https://placehold.co/40x40/A855F7/FFFFFF?text=U" 
                  alt="User" 
                  className="h-8 w-8 rounded-full" 
                />
                <div className="absolute bottom-0 right-0 h-2 w-2 rounded-full bg-green-500 border border-white dark:border-slate-800"></div>
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">John Doe</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">Admin</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className={`flex-1 overflow-y-auto transition-all duration-300 ${
        isMobile 
          ? 'mt-16' 
          : collapsed 
            ? 'md:ml-20' 
            : 'md:ml-64'
      } min-h-[calc(100vh-4rem)] md:min-h-screen`}>
        <DashboardBackground />
        <div className="relative z-10 p-4 sm:p-6 md:p-8">
          <React.Suspense fallback={<LayoutSkeleton />}>
            <Outlet />
          </React.Suspense>
        </div>
      </main>
    </div>
  );
}

const LayoutSkeleton = () => (
  <div className="space-y-6 p-1 animate-pulse">
    <div className="flex justify-between items-center">
      <Skeleton className="h-8 w-48 rounded-lg bg-gray-200 dark:bg-slate-700" />
      <Skeleton className="h-10 w-32 rounded-lg bg-gray-200 dark:bg-slate-700" />
    </div>
    <Skeleton className="h-6 w-2/3 rounded-lg bg-gray-200 dark:bg-slate-700" />
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {[1, 2, 3].map((i) => (
        <Skeleton key={i} className="h-40 w-full rounded-xl bg-gray-200 dark:bg-slate-700" />
      ))}
    </div>
    <Skeleton className="h-96 w-full rounded-xl bg-gray-200 dark:bg-slate-700" />
  </div>
);