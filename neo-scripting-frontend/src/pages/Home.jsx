import Navbar from '../components/Navbar'
import HeroSection from '../components/HeroSection'
import GeneratorForm from '../components/GeneratorForm'
import MCPSection from '../components/MCPSection'
import Footer from '../components/Footer'

export default function Home() {
  return (
    <div className="min-h-screen flex flex-col bg-bg-base">
      <Navbar />
      <main className="flex-1">
        <HeroSection />
        <GeneratorForm />
        <MCPSection />
      </main>
      <Footer />
    </div>
  )
}
