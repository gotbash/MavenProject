import config.BaseChromeDriverConfiguration;
import org.junit.Test;
import org.openqa.selenium.support.PageFactory;
import pageobjects.Login;
import testdata.TestData;

public class LoginTest extends BaseChromeDriverConfiguration{

   @Test

    public void testLogin() {

        //Instantiating Login & Profile page using initElements()
        Login login = PageFactory.initElements(driver, Login.class);
           TestData testData = new TestData();

           //Make Login
           login.makeLogin(testData.userName, testData.password);

    }

}